using System.Diagnostics;
using System.Text.Json;
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
using var httpClient = new HttpClient { Timeout = TimeSpan.FromMinutes(3) };
var gate = new SemaphoreSlim(1, 1);

async Task<IResult> RunEngine(string command, int? season, CancellationToken cancellationToken)
{
    await gate.WaitAsync(cancellationToken);
    try
    {
        string output;
        if (!string.IsNullOrEmpty(engineUrl))
        {
            var path = command switch { "seasons" => "seasons", "status" => "status", _ => $"rankings?season={season}" };
            using var response = await httpClient.GetAsync(
                new Uri(new Uri(engineUrl.TrimEnd('/') + "/"), path), cancellationToken);
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
            using var process = Process.Start(start) ?? throw new InvalidOperationException("Could not start the ranking engine.");
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            timeout.CancelAfter(TimeSpan.FromMinutes(3));
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
        gate.Release();
    }
}

app.MapGet("/api/seasons", (CancellationToken ct) => RunEngine("seasons", null, ct));
app.MapGet("/api/status", (CancellationToken ct) => RunEngine("status", null, ct));
app.MapGet("/api/rankings", (int season, CancellationToken ct) =>
    season < 2020 || season > DateTime.UtcNow.Year
        ? Task.FromResult<IResult>(Results.BadRequest(new { error = "Season must be between 2020 and the current year." }))
        : RunEngine("season", season, ct));

var webRoot = Path.Combine(root, "www");
if (Directory.Exists(webRoot))
{
    var files = new PhysicalFileProvider(webRoot);
    app.UseDefaultFiles(new DefaultFilesOptions { FileProvider = files });
    app.UseStaticFiles(new StaticFileOptions { FileProvider = files });
}
app.Run();
