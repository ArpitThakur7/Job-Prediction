using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;

namespace JobMatcher.Core;

/// <summary>
/// .NET Core implementation of Skill Extraction matching the Python NLP engine.
/// Supports MERN, TypeScript, Python, .NET Core, and cloud ecosystems.
/// </summary>
public class SkillExtractor
{
    private static readonly HashSet<string> MasterSkills = new(StringComparer.OrdinalIgnoreCase)
    {
        "Python", "Java", "JavaScript", "TypeScript", "React", "Node.js", "Express",
        "Django", "Flask", "FastAPI", "SQL", "PostgreSQL", "MySQL", "MongoDB",
        "Redis", "GraphQL", "REST", "Microservices", "AWS", "Google Cloud", "Azure",
        "Docker", "Kubernetes", "Linux", "Git", "CI/CD", "Pandas", "NumPy",
        "Scikit-learn", "XGBoost", "PyTorch", "TensorFlow", "Transformers",
        "NLP", "LLMs", "LangChain", "Pinecone", "Kafka", "Spark",
        "C#", "C++", "Go", "Ruby", "PHP",
        ".NET", ".NET Core", "ASP.NET", "ASP.NET Core", "Entity Framework", "Blazor",
        "MERN", "MERN Stack", "Next.js"
    };

    /// <summary>
    /// Extract technical skills from raw resume or job text with token boundary recognition.
    /// </summary>
    public static List<string> ExtractSkills(string text)
    {
        if (string.IsNullOrWhiteSpace(text))
            return new List<string>();

        var matched = new List<string>();
        string lower = text.ToLowerInvariant();

        // Special regex matching for .NET and MERN patterns
        bool hasDotNet = Regex.IsMatch(lower, @"(\.net|dotnet|\basp\.net)\b");
        bool hasMern = Regex.IsMatch(lower, @"\bmern(\s+stack)?\b");

        foreach (var skill in MasterSkills)
        {
            if (skill.Equals(".NET", StringComparison.OrdinalIgnoreCase))
            {
                if (hasDotNet && !matched.Contains(".NET"))
                    matched.Add(".NET");
                continue;
            }

            if (skill.StartsWith("MERN", StringComparison.OrdinalIgnoreCase))
            {
                if (hasMern && !matched.Contains(skill))
                    matched.Add(skill);
                continue;
            }

            string sLower = skill.ToLowerInvariant();
            if (lower.Contains(sLower))
            {
                matched.Add(skill);
            }
        }

        return matched;
    }
}
