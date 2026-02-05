using System.Text.Json;

namespace ODPC.Config
{
    public static class JsonSerialization
    {
        /// <summary>
        /// Options for serializing to camelCase (for frontend communication).
        /// </summary>
        public static readonly JsonSerializerOptions CamelCaseOptions = new()
        {
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase
        };

        /// <summary>
        /// Options for serializing to snake_case (for publicatiebank API).
        /// </summary>
        public static readonly JsonSerializerOptions SnakeCaseOptions = new()
        {
            PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
        };
    }
}
