using System.Diagnostics;
using System.Collections.Concurrent;
using System.Text.Json;
using Microsoft.AspNetCore.Http.HttpResults;
using Microsoft.Extensions.FileProviders;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();
var root = Path.GetFullPath(Path.Combine(app.Environment.ContentRootPath, ".."));
var python = Environment.GetEnvironmentVariable("POWERINDEX_PYTHON")
    ?? (OperatingSystem.IsWindows()
        ? Path.Combine(root, "engine", ".venv", "Scripts", "python.exe")
        : Path.Combine(root, "engine", ".venv", "bin", "python"));
var engine = Path.Combine(root, "engine", "engine.py");
var engineUrl = Environment.GetEnvironmentVariable("POWERINDEX_ENGINE_URL");
using var httpClient = new HttpClient { Timeout = Timeout.InfiniteTimeSpan };
var gate = new SemaphoreSlim(1, 1);
var playoffGate = new SemaphoreSlim(1, 1);
var progressGate = new SemaphoreSlim(1, 1);
var playoffJobs = new ConcurrentDictionary<(int Season, int Week), (Guid Id, Lazy<Task<IResult>> Task)>();

async Task<IResult> RunEngine(string command, int? season, CancellationToken cancellationToken, int? week = null, Guid? job = null)
{
    var commandGate = command == "playoffs" ? playoffGate : command == "playoff-progress" ? progressGate : gate;
    await commandGate.WaitAsync(cancellationToken);
    try
    {
        string output;
        if (!string.IsNullOrEmpty(engineUrl))
        {
            var path = command switch
            {
                "seasons" => "seasons",
                "status" => "status",
                "playoffs" => $"playoffs?season={season}&week={week}&job={job}",
                "playoff-progress" => $"playoffs/progress?job={job}",
                _ => $"rankings?season={season}"
            };
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            timeout.CancelAfter(command == "playoffs" ? TimeSpan.FromHours(24) : TimeSpan.FromMinutes(3));
            using var response = await httpClient.GetAsync(
                new Uri(new Uri(engineUrl.TrimEnd('/') + "/"), path), timeout.Token);
            if (!response.IsSuccessStatusCode)
            {
                app.Logger.LogError("Engine returned HTTP {StatusCode}", (int)response.StatusCode);
                return Results.Problem("Could not load NFL data. Check the API logs and engine setup.",
                    statusCode: response.StatusCode == System.Net.HttpStatusCode.GatewayTimeout ? 504 : 502);
            }
            output = await response.Content.ReadAsStringAsync(cancellationToken);
        }
        else
        {
            var start = new ProcessStartInfo(python)
            {
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
            };
            start.Environment["NFLREADPY_VERBOSE"] = "false";
            start.ArgumentList.Add(engine);
            start.ArgumentList.Add(command);
            if (season.HasValue)
            {
                start.ArgumentList.Add("--season");
                start.ArgumentList.Add(season.Value.ToString(System.Globalization.CultureInfo.InvariantCulture));
            }
            if (week.HasValue)
            {
                start.ArgumentList.Add("--week");
                start.ArgumentList.Add(week.Value.ToString(System.Globalization.CultureInfo.InvariantCulture));
            }
            if (job.HasValue)
            {
                start.ArgumentList.Add("--job");
                start.ArgumentList.Add(job.Value.ToString());
            }
            using var process = Process.Start(start) ?? throw new InvalidOperationException("Could not start the ranking engine.");
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            timeout.CancelAfter(command == "playoffs" ? TimeSpan.FromHours(24) : TimeSpan.FromMinutes(3));
            var outputTask = process.StandardOutput.ReadToEndAsync(timeout.Token);
            var errorTask = process.StandardError.ReadToEndAsync(timeout.Token);
            try
            {
                await process.WaitForExitAsync(timeout.Token);
            }
            catch (OperationCanceledException)
            {
                if (!process.HasExited) process.Kill(entireProcessTree: true);
                throw;
            }
            output = await outputTask;
            var error = await errorTask;
            if (process.ExitCode != 0)
                throw new InvalidOperationException($"Engine exited with code {process.ExitCode}: {error}");
        }
        using var parsed = JsonDocument.Parse(output);
        return Results.Content(output, "application/json");
    }
    catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
    {
        app.Logger.LogError("Ranking engine timed out for {Command} {Season}", command, season);
        return Results.Problem("The ranking engine timed out. Please try again.", statusCode: 504);
    }
    catch (Exception ex) when (ex is not OperationCanceledException)
    {
        app.Logger.LogError(ex, "Ranking engine failed for {Command} {Season}", command, season);
        return Results.Problem("Could not load NFL data. Check the API logs and engine setup.", statusCode: 502);
    }
    finally
    {
        commandGate.Release();
    }
}

app.MapGet("/api/seasons", (CancellationToken ct) => RunEngine("seasons", null, ct));
app.MapGet("/api/status", (CancellationToken ct) => RunEngine("status", null, ct));
app.MapGet("/api/rankings", (int season, CancellationToken ct) =>
    season < 2020 || season > DateTime.UtcNow.Year
        ? Task.FromResult<IResult>(Results.BadRequest(new { error = "Season must be between 2020 and the current year." }))
        : RunEngine("season", season, ct));
app.MapGet("/api/playoffs", async (int season, int week) =>
{
    if (season < 2020 || season > DateTime.UtcNow.Year || week < 1 || week > 18)
        return Results.BadRequest(new { error = "A valid season and week are required." });
    var key = (season, week);
    var job = playoffJobs.GetOrAdd(key, _ =>
    {
        var id = Guid.NewGuid();
        return (id, new Lazy<Task<IResult>>(
            () => RunEngine("playoffs", season, CancellationToken.None, week, id)));
    });
    var task = job.Task.Value;
    if (!task.IsCompleted)
        await Task.WhenAny(task, Task.Delay(TimeSpan.FromSeconds(2)));
    if (!task.IsCompleted)
    {
        var progress = await RunEngine("playoff-progress", null, CancellationToken.None, job: job.Id);
        if (progress is not ContentHttpResult content)
            return progress;
        using var json = JsonDocument.Parse(content.ResponseContent!);
        return Results.Json(new { status = "pending", progress = json.RootElement.Clone() }, statusCode: 202);
    }
    ((ICollection<KeyValuePair<(int Season, int Week), (Guid Id, Lazy<Task<IResult>> Task)>>)playoffJobs)
        .Remove(new(key, job));
    return await task;
});
var webRoot = Path.Combine(root, "www");
if (Directory.Exists(webRoot))
{
    var files = new PhysicalFileProvider(webRoot);
    app.UseDefaultFiles(new DefaultFilesOptions { FileProvider = files });
    app.UseStaticFiles(new StaticFileOptions
    {
        FileProvider = files,
        OnPrepareResponse = context => context.Context.Response.Headers.CacheControl = "no-cache",
    });
}
app.Run();
