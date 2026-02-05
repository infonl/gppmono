using System.Text.Json;
using Microsoft.AspNetCore.Mvc;
using ODPC.Apis.Odrc;
using ODPC.Authentication;
using ODPC.Config;

namespace ODPC.Features.Documenten.DocumentBijwerken
{
    [ApiController]
    public class DocumentBijwerkenController(IOdrcClientFactory clientFactory, OdpcUser user) : ControllerBase
    {
        [HttpPut("api/{version}/documenten/{uuid:guid}")]
        public async Task<IActionResult> Put(string version, Guid uuid, PublicatieDocument document, CancellationToken token)
        {
            using var client = clientFactory.Create("Document bijwerken");

            var url = $"/api/{version}/documenten/{uuid}";

            // document ophalen
            using var getResponse = await client.GetAsync(url, HttpCompletionOption.ResponseHeadersRead, token);

            if (!getResponse.IsSuccessStatusCode)
            {
                return StatusCode(502);
            }

            var json = await getResponse.Content.ReadFromJsonAsync<PublicatieDocument>(token);

            if (json?.Eigenaar?.identifier != user.Id)
            {
                return NotFound();
            }

            // document bijwerken
            var jsonContent = JsonSerializer.Serialize(document, JsonSerialization.CamelCaseOptions);
            using var content = new StringContent(jsonContent, System.Text.Encoding.UTF8, "application/json");
            using var putResponse = await client.PutAsync(url, content, token);

            putResponse.EnsureSuccessStatusCode();

            var viewModel = await putResponse.Content.ReadFromJsonAsync<PublicatieDocument>(token);

            return Ok(viewModel);
        }
    }
}
