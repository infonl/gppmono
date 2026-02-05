using System.Text.Json;
using Microsoft.AspNetCore.Mvc;
using ODPC.Apis.Odrc;
using ODPC.Config;
using ODPC.Data;

namespace ODPC.Features.Publicaties.PublicatieRegistreren
{
    [ApiController]
    public class PublicatieRegistrerenController(
        IOdrcClientFactory clientFactory,
        IGebruikerWaardelijstItemsService waardelijstItemsService,
        ILogger<PublicatieRegistrerenController> logger) : ControllerBase
    {
        [HttpPost("api/{version}/publicaties")]
        public async Task<IActionResult> Post(string version, Publicatie publicatie, CancellationToken token)
        {
            // Debug: Log the incoming publicatie
            logger.LogInformation("Received publicatie: Publisher={Publisher}, OfficieleTitel={OfficieleTitel}, InformatieCategorieen={InformatieCategorieen}",
                publicatie.Publisher, publicatie.OfficieleTitel, publicatie.InformatieCategorieen != null ? string.Join(",", publicatie.InformatieCategorieen) : "null");

            Guid? eigenaarGroepIdentifier = Guid.TryParse(publicatie.EigenaarGroep?.identifier, out var identifier)
                ? identifier
                : null;

            var gebruikersgroepWaardelijstUuids = await waardelijstItemsService.GetAsync(eigenaarGroepIdentifier, token);

            if (publicatie.EigenaarGroep == null)
            {
                ModelState.AddModelError(nameof(publicatie.EigenaarGroep), "Publicatie is niet gekoppeld aan een gebruikergroep");
                return BadRequest(ModelState);
            }

            if (!string.IsNullOrEmpty(publicatie.Publisher) && !gebruikersgroepWaardelijstUuids.Contains(publicatie.Publisher))
            {
                ModelState.AddModelError(nameof(publicatie.Publisher), "Gebruiker is niet geautoriseerd voor deze organisatie");
                return BadRequest(ModelState);
            }

            if (publicatie.InformatieCategorieen != null && publicatie.InformatieCategorieen.Any(c => !gebruikersgroepWaardelijstUuids.Contains(c)))
            {
                ModelState.AddModelError(nameof(publicatie.InformatieCategorieen), "Gebruiker is niet geautoriseerd voor deze informatiecategorieën");
                return BadRequest(ModelState);
            }

            if (publicatie.Onderwerpen != null && publicatie.Onderwerpen.Any(c => !gebruikersgroepWaardelijstUuids.Contains(c)))
            {
                ModelState.AddModelError(nameof(publicatie.Onderwerpen), "Gebruiker is niet geautoriseerd voor deze onderwerpen");
                return BadRequest(ModelState);
            }

            // PUBLICATIEBANK

            using var client = clientFactory.Create("Publicatie registreren");

            var url = $"/api/{version}/publicaties";

            // Debug: Log the JSON that will be sent (publicatiebank expects camelCase, uses CamelCaseJSONParser)
            var jsonToSend = JsonSerializer.Serialize(publicatie, JsonSerialization.CamelCaseOptions);
            logger.LogInformation("Sending JSON to publicatiebank: {Json}", jsonToSend);

            // Manually create StringContent to ensure proper serialization
            using var content = new StringContent(jsonToSend, System.Text.Encoding.UTF8, "application/json");
            using var response = await client.PostAsync(url, content, token);

            if (!response.IsSuccessStatusCode)
            {
                var errorContent = await response.Content.ReadAsStringAsync(token);
                logger.LogError("Publicatiebank returned {StatusCode}: {ErrorContent}", (int)response.StatusCode, errorContent);
            }

            response.EnsureSuccessStatusCode();

            var viewModel = await response.Content.ReadFromJsonAsync<Publicatie>(token);

            return viewModel == null ? NotFound() : Ok(viewModel);
        }
    }
}
