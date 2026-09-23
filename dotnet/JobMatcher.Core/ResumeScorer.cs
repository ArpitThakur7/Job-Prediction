using System;
using System.Collections.Generic;
using System.Linq;

namespace JobMatcher.Core;

public class CandidateProfile
{
    public string CandidateName { get; set; } = string.Empty;
    public string Email { get; set; } = string.Empty;
    public double ExperienceYears { get; set; }
    public string Education { get; set; } = "Bachelors";
    public List<string> Skills { get; set; } = new();
}

public class JobRequirement
{
    public string JobId { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public string Company { get; set; } = string.Empty;
    public List<string> RequiredSkills { get; set; } = new();
    public double MinExperienceYears { get; set; }
}

public class MatchScoreResult
{
    public double MatchScore { get; set; }
    public int SkillsDepthScore { get; set; }
    public int ExperienceScore { get; set; }
    public int EducationScore { get; set; }
    public List<string> MatchedSkills { get; set; } = new();
    public List<string> MissingSkills { get; set; } = new();
    public string Grade { get; set; } = string.Empty;
}

/// <summary>
/// .NET Core implementation of ATS Scoring & Match Prediction.
/// Calculates weighted compatibility across skills, experience, and educational background.
/// </summary>
public class ResumeScorer
{
    public static MatchScoreResult ScoreCompatibility(CandidateProfile candidate, JobRequirement job)
    {
        var candidateSkillsLower = new HashSet<string>(candidate.Skills.Select(s => s.ToLowerInvariant()));
        var matched = new List<string>();
        var missing = new List<string>();

        foreach (var req in job.RequiredSkills)
        {
            if (candidateSkillsLower.Contains(req.ToLowerInvariant()))
            {
                matched.Add(req);
            }
            else
            {
                missing.Add(req);
            }
        }

        // Skills Depth Score (0-100)
        double skillRatio = job.RequiredSkills.Count > 0 
            ? (double)matched.Count / job.RequiredSkills.Count 
            : 1.0;
        int skillsScore = (int)Math.Round(Math.Clamp(skillRatio * 100.0, 0, 100));

        // Experience Score (0-100)
        int expScore = job.MinExperienceYears > 0 
            ? (int)Math.Round(Math.Clamp((candidate.ExperienceYears / job.MinExperienceYears) * 100.0, 0, 100))
            : (int)Math.Min(100, candidate.ExperienceYears * 15);

        // Education Score
        int eduScore = candidate.Education.Contains("Master", StringComparison.OrdinalIgnoreCase) ||
                       candidate.Education.Contains("PhD", StringComparison.OrdinalIgnoreCase)
            ? 100
            : 85;

        // Weighted Overall Match Score (Skills: 50%, Experience: 35%, Education: 15%)
        double overallScore = Math.Round((skillsScore * 0.50) + (expScore * 0.35) + (eduScore * 0.15), 1);

        string grade = overallScore switch
        {
            >= 90 => "Exceptional Match",
            >= 80 => "Strong Match",
            >= 70 => "Moderate Match",
            _ => "Emerging Fit"
        };

        return new MatchScoreResult
        {
            MatchScore = overallScore,
            SkillsDepthScore = skillsScore,
            ExperienceScore = expScore,
            EducationScore = eduScore,
            MatchedSkills = matched,
            MissingSkills = missing,
            Grade = grade
        };
    }
}
