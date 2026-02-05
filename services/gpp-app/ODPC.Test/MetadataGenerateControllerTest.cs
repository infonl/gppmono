using System.Net;
using System.Text;
using System.Text.Json.Nodes;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Infrastructure;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using Moq;
using Moq.Protected;
using ODPC.Features.Metadata;

namespace ODPC.Test
{
    [TestClass]
    public class MetadataGenerateControllerTest
    {
        private Mock<IHttpClientFactory> _httpClientFactoryMock = null!;
        private Mock<IConfiguration> _configMock = null!;
        private Mock<ILogger<MetadataGenerateController>> _loggerMock = null!;

        [TestInitialize]
        public void Setup()
        {
            _httpClientFactoryMock = new Mock<IHttpClientFactory>();
            _configMock = new Mock<IConfiguration>();
            _loggerMock = new Mock<ILogger<MetadataGenerateController>>();
        }

        #region Health Endpoint Tests

        [TestMethod]
        public async Task Health_ReturnsServiceUnavailable_WhenWooHooUrlNotConfigured()
        {
            // Arrange
            _configMock.Setup(c => c["WOO_HOO_BASE_URL"]).Returns((string?)null);

            var controller = new MetadataGenerateController(
                _httpClientFactoryMock.Object,
                _configMock.Object,
                _loggerMock.Object
            );

            // Act
            var result = await controller.Health(CancellationToken.None);

            // Assert
            var statusCodeResult = result as IStatusCodeActionResult;
            Assert.IsNotNull(statusCodeResult);
            Assert.AreEqual(503, statusCodeResult.StatusCode);
        }

        [TestMethod]
        public async Task Health_ReturnsOk_WhenWooHooHealthy()
        {
            // Arrange
            _configMock.Setup(c => c["WOO_HOO_BASE_URL"]).Returns("http://woo-hoo:8003");
            _configMock.Setup(c => c["WOO_HOO_HEALTH_TIMEOUT_SECONDS"]).Returns("5");

            var mockHandler = new Mock<HttpMessageHandler>();
            mockHandler.Protected()
                .Setup<Task<HttpResponseMessage>>(
                    "SendAsync",
                    ItExpr.IsAny<HttpRequestMessage>(),
                    ItExpr.IsAny<CancellationToken>())
                .ReturnsAsync(new HttpResponseMessage(HttpStatusCode.OK));

            var httpClient = new HttpClient(mockHandler.Object);
            _httpClientFactoryMock.Setup(f => f.CreateClient("WooHoo")).Returns(httpClient);

            var controller = new MetadataGenerateController(
                _httpClientFactoryMock.Object,
                _configMock.Object,
                _loggerMock.Object
            );

            // Act
            var result = await controller.Health(CancellationToken.None);

            // Assert
            Assert.IsInstanceOfType(result, typeof(OkResult));
        }

        [TestMethod]
        public async Task Health_ReturnsBadGateway_WhenWooHooUnhealthy()
        {
            // Arrange
            _configMock.Setup(c => c["WOO_HOO_BASE_URL"]).Returns("http://woo-hoo:8003");
            _configMock.Setup(c => c["WOO_HOO_HEALTH_TIMEOUT_SECONDS"]).Returns("5");

            var mockHandler = new Mock<HttpMessageHandler>();
            mockHandler.Protected()
                .Setup<Task<HttpResponseMessage>>(
                    "SendAsync",
                    ItExpr.IsAny<HttpRequestMessage>(),
                    ItExpr.IsAny<CancellationToken>())
                .ReturnsAsync(new HttpResponseMessage(HttpStatusCode.ServiceUnavailable));

            var httpClient = new HttpClient(mockHandler.Object);
            _httpClientFactoryMock.Setup(f => f.CreateClient("WooHoo")).Returns(httpClient);

            var controller = new MetadataGenerateController(
                _httpClientFactoryMock.Object,
                _configMock.Object,
                _loggerMock.Object
            );

            // Act
            var result = await controller.Health(CancellationToken.None);

            // Assert
            var statusCodeResult = result as IStatusCodeActionResult;
            Assert.IsNotNull(statusCodeResult);
            Assert.AreEqual(502, statusCodeResult.StatusCode);
        }

        [TestMethod]
        public async Task Health_ReturnsBadGateway_WhenExceptionThrown()
        {
            // Arrange
            _configMock.Setup(c => c["WOO_HOO_BASE_URL"]).Returns("http://woo-hoo:8003");
            _configMock.Setup(c => c["WOO_HOO_HEALTH_TIMEOUT_SECONDS"]).Returns("5");

            var mockHandler = new Mock<HttpMessageHandler>();
            mockHandler.Protected()
                .Setup<Task<HttpResponseMessage>>(
                    "SendAsync",
                    ItExpr.IsAny<HttpRequestMessage>(),
                    ItExpr.IsAny<CancellationToken>())
                .ThrowsAsync(new HttpRequestException("Connection refused"));

            var httpClient = new HttpClient(mockHandler.Object);
            _httpClientFactoryMock.Setup(f => f.CreateClient("WooHoo")).Returns(httpClient);

            var controller = new MetadataGenerateController(
                _httpClientFactoryMock.Object,
                _configMock.Object,
                _loggerMock.Object
            );

            // Act
            var result = await controller.Health(CancellationToken.None);

            // Assert
            var statusCodeResult = result as IStatusCodeActionResult;
            Assert.IsNotNull(statusCodeResult);
            Assert.AreEqual(502, statusCodeResult.StatusCode);
        }

        #endregion

        #region Generate Endpoint Tests

        [TestMethod]
        public async Task Post_ReturnsServiceUnavailable_WhenWooHooUrlNotConfigured()
        {
            // Arrange
            _configMock.Setup(c => c["WOO_HOO_BASE_URL"]).Returns((string?)null);

            var controller = new MetadataGenerateController(
                _httpClientFactoryMock.Object,
                _configMock.Object,
                _loggerMock.Object
            );

            // Act
            var result = await controller.Post(Guid.NewGuid(), CancellationToken.None);

            // Assert
            var statusCodeResult = result as ObjectResult;
            Assert.IsNotNull(statusCodeResult);
            Assert.AreEqual(503, statusCodeResult.StatusCode);
            Assert.IsTrue(statusCodeResult.Value?.ToString()?.Contains("not configured") ?? false);
        }

        [TestMethod]
        public async Task Post_ReturnsBadGateway_WhenOdrcDownloadFails()
        {
            // Arrange
            var documentUuid = Guid.NewGuid();
            _configMock.Setup(c => c["WOO_HOO_BASE_URL"]).Returns("http://woo-hoo:8003");
            _configMock.Setup(c => c["ODRC_BASE_URL"]).Returns("http://odrc:8000");
            _configMock.Setup(c => c["ODRC_API_KEY"]).Returns("test-api-key");

            var mockHandler = new Mock<HttpMessageHandler>();
            mockHandler.Protected()
                .Setup<Task<HttpResponseMessage>>(
                    "SendAsync",
                    ItExpr.Is<HttpRequestMessage>(r => r.RequestUri!.ToString().Contains("/download")),
                    ItExpr.IsAny<CancellationToken>())
                .ReturnsAsync(new HttpResponseMessage(HttpStatusCode.NotFound));

            var httpClient = new HttpClient(mockHandler.Object);
            _httpClientFactoryMock.Setup(f => f.CreateClient(It.IsAny<string>())).Returns(httpClient);

            var controller = new MetadataGenerateController(
                _httpClientFactoryMock.Object,
                _configMock.Object,
                _loggerMock.Object
            );

            // Act
            var result = await controller.Post(documentUuid, CancellationToken.None);

            // Assert
            var statusCodeResult = result as ObjectResult;
            Assert.IsNotNull(statusCodeResult);
            Assert.AreEqual(502, statusCodeResult.StatusCode);
            Assert.IsTrue(statusCodeResult.Value?.ToString()?.Contains("download") ?? false);
        }

        [TestMethod]
        public async Task Post_ReturnsOk_WhenMetadataGeneratedSuccessfully()
        {
            // Arrange
            var documentUuid = Guid.NewGuid();
            _configMock.Setup(c => c["WOO_HOO_BASE_URL"]).Returns("http://woo-hoo:8003");
            _configMock.Setup(c => c["ODRC_BASE_URL"]).Returns("http://odrc:8000");
            _configMock.Setup(c => c["ODRC_API_KEY"]).Returns("test-api-key");
            _configMock.Setup(c => c["WOO_HOO_GENERATE_TIMEOUT_SECONDS"]).Returns("60");

            var pdfContent = new byte[] { 0x25, 0x50, 0x44, 0x46 }; // PDF magic bytes
            var metadataJson = "{\"bestandsnaam\": \"test.pdf\"}";
            var generatedMetadata = "{\"success\": true, \"suggestion\": {\"metadata\": {}}}";

            // Create separate handlers for ODRC and WooHoo clients
            var odrcHandler = new Mock<HttpMessageHandler>();
            odrcHandler.Protected()
                .Setup<Task<HttpResponseMessage>>(
                    "SendAsync",
                    ItExpr.IsAny<HttpRequestMessage>(),
                    ItExpr.IsAny<CancellationToken>())
                .ReturnsAsync((HttpRequestMessage request, CancellationToken _) =>
                {
                    var uri = request.RequestUri?.ToString() ?? "";
                    if (uri.Contains("/download"))
                    {
                        return new HttpResponseMessage(HttpStatusCode.OK)
                        {
                            Content = new ByteArrayContent(pdfContent)
                        };
                    }
                    return new HttpResponseMessage(HttpStatusCode.OK)
                    {
                        Content = new StringContent(metadataJson, Encoding.UTF8, "application/json")
                    };
                });

            var wooHooHandler = new Mock<HttpMessageHandler>();
            wooHooHandler.Protected()
                .Setup<Task<HttpResponseMessage>>(
                    "SendAsync",
                    ItExpr.IsAny<HttpRequestMessage>(),
                    ItExpr.IsAny<CancellationToken>())
                .ReturnsAsync(new HttpResponseMessage(HttpStatusCode.OK)
                {
                    Content = new StringContent(generatedMetadata, Encoding.UTF8, "application/json")
                });

            var odrcClient = new HttpClient(odrcHandler.Object);
            var wooHooClient = new HttpClient(wooHooHandler.Object);

            // Default client (empty string) for ODRC, named "WooHoo" for woo-hoo
            _httpClientFactoryMock.Setup(f => f.CreateClient(string.Empty)).Returns(odrcClient);
            _httpClientFactoryMock.Setup(f => f.CreateClient("WooHoo")).Returns(wooHooClient);

            var controller = new MetadataGenerateController(
                _httpClientFactoryMock.Object,
                _configMock.Object,
                _loggerMock.Object
            );

            // Act
            var result = await controller.Post(documentUuid, CancellationToken.None);

            // Assert
            var okResult = result as OkObjectResult;
            Assert.IsNotNull(okResult, $"Expected OkObjectResult but got {result?.GetType().Name}");
            Assert.IsNotNull(okResult.Value);
        }

        [TestMethod]
        public async Task Post_ReturnsBadGateway_WhenWooHooGenerationFails()
        {
            // Arrange
            var documentUuid = Guid.NewGuid();
            _configMock.Setup(c => c["WOO_HOO_BASE_URL"]).Returns("http://woo-hoo:8003");
            _configMock.Setup(c => c["ODRC_BASE_URL"]).Returns("http://odrc:8000");
            _configMock.Setup(c => c["ODRC_API_KEY"]).Returns("test-api-key");
            _configMock.Setup(c => c["WOO_HOO_GENERATE_TIMEOUT_SECONDS"]).Returns("60");

            var pdfContent = new byte[] { 0x25, 0x50, 0x44, 0x46 };
            var metadataJson = "{\"bestandsnaam\": \"test.pdf\"}";

            // Create separate handlers for ODRC and WooHoo clients
            var odrcHandler = new Mock<HttpMessageHandler>();
            odrcHandler.Protected()
                .Setup<Task<HttpResponseMessage>>(
                    "SendAsync",
                    ItExpr.IsAny<HttpRequestMessage>(),
                    ItExpr.IsAny<CancellationToken>())
                .ReturnsAsync((HttpRequestMessage request, CancellationToken _) =>
                {
                    var uri = request.RequestUri?.ToString() ?? "";
                    if (uri.Contains("/download"))
                    {
                        return new HttpResponseMessage(HttpStatusCode.OK)
                        {
                            Content = new ByteArrayContent(pdfContent)
                        };
                    }
                    return new HttpResponseMessage(HttpStatusCode.OK)
                    {
                        Content = new StringContent(metadataJson, Encoding.UTF8, "application/json")
                    };
                });

            var wooHooHandler = new Mock<HttpMessageHandler>();
            wooHooHandler.Protected()
                .Setup<Task<HttpResponseMessage>>(
                    "SendAsync",
                    ItExpr.IsAny<HttpRequestMessage>(),
                    ItExpr.IsAny<CancellationToken>())
                .ReturnsAsync(new HttpResponseMessage(HttpStatusCode.InternalServerError)
                {
                    Content = new StringContent("{\"error\": \"LLM service unavailable\"}", Encoding.UTF8, "application/json")
                });

            var odrcClient = new HttpClient(odrcHandler.Object);
            var wooHooClient = new HttpClient(wooHooHandler.Object);

            _httpClientFactoryMock.Setup(f => f.CreateClient(string.Empty)).Returns(odrcClient);
            _httpClientFactoryMock.Setup(f => f.CreateClient("WooHoo")).Returns(wooHooClient);

            var controller = new MetadataGenerateController(
                _httpClientFactoryMock.Object,
                _configMock.Object,
                _loggerMock.Object
            );

            // Act
            var result = await controller.Post(documentUuid, CancellationToken.None);

            // Assert
            var statusCodeResult = result as ObjectResult;
            Assert.IsNotNull(statusCodeResult);
            Assert.AreEqual(502, statusCodeResult.StatusCode);
        }

        [TestMethod]
        public async Task Post_SetsCorrectAuditHeaders()
        {
            // Arrange
            var documentUuid = Guid.NewGuid();
            _configMock.Setup(c => c["WOO_HOO_BASE_URL"]).Returns("http://woo-hoo:8003");
            _configMock.Setup(c => c["ODRC_BASE_URL"]).Returns("http://odrc:8000");
            _configMock.Setup(c => c["ODRC_API_KEY"]).Returns("test-api-key");

            HttpRequestMessage? capturedRequest = null;

            var mockHandler = new Mock<HttpMessageHandler>();
            mockHandler.Protected()
                .Setup<Task<HttpResponseMessage>>(
                    "SendAsync",
                    ItExpr.Is<HttpRequestMessage>(r => r.RequestUri!.ToString().Contains("/download")),
                    ItExpr.IsAny<CancellationToken>())
                .Callback<HttpRequestMessage, CancellationToken>((req, _) => capturedRequest = req)
                .ReturnsAsync(new HttpResponseMessage(HttpStatusCode.NotFound));

            var httpClient = new HttpClient(mockHandler.Object);
            _httpClientFactoryMock.Setup(f => f.CreateClient(It.IsAny<string>())).Returns(httpClient);

            var controller = new MetadataGenerateController(
                _httpClientFactoryMock.Object,
                _configMock.Object,
                _loggerMock.Object
            );

            // Act
            await controller.Post(documentUuid, CancellationToken.None);

            // Assert
            Assert.IsNotNull(capturedRequest);
            Assert.IsTrue(capturedRequest.Headers.Contains("Audit-User-ID"));
            Assert.IsTrue(capturedRequest.Headers.Contains("Audit-User-Representation"));
            Assert.IsTrue(capturedRequest.Headers.Contains("Audit-Remarks"));
            Assert.AreEqual("odpc-metadata-service", capturedRequest.Headers.GetValues("Audit-User-ID").First());
        }

        #endregion
    }
}
