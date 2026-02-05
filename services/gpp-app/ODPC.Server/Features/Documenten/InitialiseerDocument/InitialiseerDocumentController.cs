using System.Text.Json;
using Microsoft.AspNetCore.Mvc;
using ODPC.Apis.Odrc;
using ODPC.Config;

namespace ODPC.Features.Documenten.InitialiseerDocument
{
    [ApiController]
    public class InitialiseerDocumentController(IOdrcClientFactory clientFactory) : ControllerBase
    {
        [HttpPost("api/{version}/documenten")]
        public async Task<IActionResult> Post(string version, PublicatieDocument document, CancellationToken token)
        {
            using var client = clientFactory.Create("Initialiseer document");

            var url = $"/api/{version}/documenten";

            var jsonContent = JsonSerializer.Serialize(document, JsonSerialization.CamelCaseOptions);
            using var content = new StringContent(jsonContent, System.Text.Encoding.UTF8, "application/json");
            using var response = await client.PostAsync(url, content, token);

            response.EnsureSuccessStatusCode();

            var viewModel = await response.Content.ReadFromJsonAsync<PublicatieDocument>(token);

            return Ok(viewModel);
        }
    }
}
