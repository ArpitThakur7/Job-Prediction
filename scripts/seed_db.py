from __future__ import annotations

import os
import sys
import pandas as pd
import numpy as np
import bcrypt
import logging
from datetime import datetime
import uuid

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import get_collection
from backend.services.embedder import generate_embedding
from backend.services.vector_store import upsert_batch

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("seed_db")

def seed():
    logger.info("Initializing Database Seed...")
    
    # 1. Seed Users
    logger.info("Seeding Users...")
    users_col = get_collection("users")
    if users_col is None:
        logger.warning("MongoDB is offline or unreachable. Seeding RAG vector store directly from CSV datasets...")
        _seed_local_memory_fallback()
        return
    
    # Clear existing mock users
    users_col.delete_many({"email": {"$in": ["seeker@example.com", "recruiter@example.com"]}})
    
    hashed_pwd = bcrypt.hashpw("password123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    
    seeker_id = "user_seeker_123"
    recruiter_id = "user_recruiter_123"
    
    users = [
        {
            "id": seeker_id,
            "email": "seeker@example.com",
            "full_name": "John Seeker",
            "role": "job_seeker",
            "hashed_password": hashed_pwd,
            "created_at": datetime.utcnow()
        },
        {
            "id": recruiter_id,
            "email": "recruiter@example.com",
            "full_name": "Jane Recruiter",
            "role": "recruiter",
            "hashed_password": hashed_pwd,
            "created_at": datetime.utcnow()
        }
    ]
    
    users_col.insert_many(users)
    logger.info("Successfully seeded users: seeker@example.com and recruiter@example.com")

    # 2. Seed Jobs
    logger.info("Seeding Jobs...")
    jobs_col = get_collection("jobs")
    jobs_col.delete_many({})

    # High-affinity tech stack benchmark jobs (MERN, .NET, Python, TypeScript)
    tech_stack_jobs = [
        {
            "job_id": "job_stack_mern_01",
            "title": "Senior MERN Stack Engineer",
            "company": "Nexus Web Systems",
            "location": "San Francisco, CA (Remote)",
            "required_skills": ["MERN", "MongoDB", "Express", "React", "Node.js", "TypeScript", "REST", "Docker"],
            "salary_min": 140000,
            "salary_max": 185000,
            "job_type": "FULL_TIME",
            "category": "Engineering",
            "industry": "Web Technology",
            "description": "Architect and maintain high-performance web applications using MERN (MongoDB, Express, React, Node.js) with TypeScript. Build robust RESTful APIs, optimize MongoDB document pipelines, and deploy containerized services.",
            "posted_by": recruiter_id,
            "created_at": datetime.utcnow(),
            "is_active": True,
        },
        {
            "job_id": "job_stack_dotnet_01",
            "title": "Principal .NET / C# Cloud Architect",
            "company": "Enterprise Global FinTech",
            "location": "New York, NY (Hybrid)",
            "required_skills": [".NET", ".NET Core", "C#", "ASP.NET Core", "Entity Framework", "Azure", "Microservices", "SQL"],
            "salary_min": 160000,
            "salary_max": 220000,
            "job_type": "FULL_TIME",
            "category": "Engineering",
            "industry": "Financial Technology",
            "description": "Lead enterprise microservices architecture using modern .NET 8 / ASP.NET Core and C#. Responsible for high-throughput distributed architectures, Entity Framework Core query optimization, Azure Service Bus, and secure cloud API gateways.",
            "posted_by": recruiter_id,
            "created_at": datetime.utcnow(),
            "is_active": True,
        },
        {
            "job_id": "job_stack_python_01",
            "title": "Lead Python & AI Systems Engineer",
            "company": "Cognitive AI Labs",
            "location": "Austin, TX (Remote)",
            "required_skills": ["Python", "FastAPI", "PyTorch", "LangChain", "Transformers", "Docker", "Pinecone", "NLP"],
            "salary_min": 155000,
            "salary_max": 210000,
            "job_type": "FULL_TIME",
            "category": "Data Science",
            "industry": "Artificial Intelligence",
            "description": "Design and productionize neural AI systems using Python and FastAPI. Build RAG knowledge pipelines with LangChain and Pinecone vector search, fine-tune transformer models with PyTorch, and deliver low-latency inference endpoints.",
            "posted_by": recruiter_id,
            "created_at": datetime.utcnow(),
            "is_active": True,
        },
        {
            "job_id": "job_stack_typescript_01",
            "title": "Senior Full-Stack TypeScript Engineer",
            "company": "ModernScale Platform",
            "location": "Seattle, WA (Remote)",
            "required_skills": ["TypeScript", "React", "Next.js", "Node.js", "GraphQL", "Tailwind CSS", "CI/CD"],
            "salary_min": 145000,
            "salary_max": 190000,
            "job_type": "FULL_TIME",
            "category": "Engineering",
            "industry": "SaaS Platform",
            "description": "Spearhead end-to-end fullstack development in pure TypeScript across Next.js React frontend and Node.js backend microservices. Deliver rich 3D and interactive user interfaces with Tailwind CSS and GraphQL APIs.",
            "posted_by": recruiter_id,
            "created_at": datetime.utcnow(),
            "is_active": True,
        },
    ]
    
    jobs_csv_path = "data/processed/jobs_clean.csv"
    if not os.path.exists(jobs_csv_path):
        logger.error(f"Processed jobs CSV not found at {jobs_csv_path}. Run prepare_dataset.py first.")
        return
        
    df_jobs = pd.read_csv(jobs_csv_path)
    # Seed top 100 jobs for performance
    df_jobs_seed = df_jobs.head(100)
    
    seeded_jobs = list(tech_stack_jobs)
    vector_payloads = []

    # Add embedding vectors for benchmark tech stack jobs
    for bj in tech_stack_jobs:
        emb_text = f"Job Title: {bj['title']}\nCompany: {bj['company']}\nCategory: {bj['category']}\nLocation: {bj['location']}\nRequired Skills: {', '.join(bj['required_skills'])}\nDescription: {bj['description']}"
        try:
            vec = generate_embedding(emb_text)
            vector_payloads.append({
                "id": f"job_{bj['job_id']}",
                "values": vec,
                "metadata": {
                    "type": "job",
                    "job_id": bj["job_id"],
                    "title": bj["title"],
                    "company": bj["company"],
                    "category": bj["category"],
                    "skills": ", ".join(bj["required_skills"]),
                    "text": emb_text[:1000]
                }
            })
        except Exception as e:
            logger.warning(f"Failed to generate embedding for benchmark job {bj['job_id']}: {e}")
    
    for _, row in df_jobs_seed.iterrows():
        job_id = str(row["job_id"])
        
        required_skills = [s.strip() for s in str(row["required_skills"]).split(",") if s.strip()]
        
        # Convert nan or empty fields to standard defaults
        sal_min = int(row["salary_min"]) if not pd.isna(row["salary_min"]) else 0
        sal_max = int(row["salary_max"]) if not pd.isna(row["salary_max"]) else 0
        
        job_doc = {
            "job_id": job_id,
            "title": str(row["title"]),
            "description": str(row["description"]),
            "company": str(row["company"]),
            "location": str(row["location"]),
            "required_skills": required_skills,
            "salary_min": sal_min,
            "salary_max": sal_max,
            "job_type": str(row["job_type"]),
            "category": str(row["category"]),
            "industry": str(row["industry"]),
            "posted_by": recruiter_id,
            "created_at": datetime.utcnow(),
            "is_active": True
        }
        seeded_jobs.append(job_doc)
        
        # Build embedding text
        emb_text = f"Job Title: {job_doc['title']}\nCompany: {job_doc['company']}\nCategory: {job_doc['category']}\nLocation: {job_doc['location']}\nRequired Skills: {', '.join(job_doc['required_skills'])}\nDescription: {job_doc['description']}"
        try:
            vec = generate_embedding(emb_text)
            vector_payloads.append({
                "id": f"job_{job_id}",
                "values": vec,
                "metadata": {
                    "type": "job",
                    "job_id": job_id,
                    "title": job_doc["title"],
                    "company": job_doc["company"],
                    "category": job_doc["category"],
                    "skills": ", ".join(job_doc["required_skills"]),
                    "text": emb_text[:1000] # store truncated summary for search RAG context
                }
            })
        except Exception as e:
            logger.warning(f"Failed to generate embedding for job {job_id}: {e}")

    jobs_col.insert_many(seeded_jobs)
    logger.info(f"Seeded {len(seeded_jobs)} jobs to MongoDB.")
    
    # 3. Seed Resumes
    logger.info("Seeding Resumes...")
    resumes_col = get_collection("resumes")
    resumes_col.delete_many({})

    # Benchmark resumes representing the 4 core tech stacks
    tech_stack_resumes = [
        {
            "resume_id": "res_stack_mern_01",
            "candidate_name": "Alex Chen",
            "email": "alex.chen@example.com",
            "phone": "+1-555-0192",
            "skills": ["MERN", "MongoDB", "Express", "React", "Node.js", "TypeScript", "REST", "Git", "Docker"],
            "experience_years": 5.5,
            "education": "Bachelor of Science in Computer Science",
            "category": "Engineering",
            "raw_text": "Alex Chen\nSenior Full-Stack MERN Developer\nalex.chen@example.com | +1-555-0192 | San Francisco, CA\n\nPROFESSIONAL SUMMARY\nExperienced Full-Stack Developer with 5.5+ years building scalable web applications using the MERN stack (MongoDB, Express.js, React, Node.js) and TypeScript.\n\nWORK EXPERIENCE\nSenior Full-Stack Engineer — CloudWave Inc (2021 - Present)\n• Designed and maintained MERN stack microservices serving 500k+ daily active users.\n• Migrated legacy REST services to Node.js and Express with TypeScript, reducing latency by 35%.\n• Optimized MongoDB aggregation pipelines and indexing strategies, decreasing DB CPU usage by 40%.\n• Built reactive component libraries in React and Tailwind CSS.\n\nSKILLS\nMERN Stack, MongoDB, Express, React, Node.js, TypeScript, REST APIs, Docker, Git, Redis.",
            "user_id": seeker_id,
            "created_at": datetime.utcnow(),
            "file_url": "http://example.com/resumes/res_stack_mern_01.pdf"
        },
        {
            "resume_id": "res_stack_dotnet_01",
            "candidate_name": "Sarah Jenkins",
            "email": "sarah.jenkins@example.com",
            "phone": "+1-555-0144",
            "skills": [".NET", ".NET Core", "C#", "ASP.NET Core", "Entity Framework", "Azure", "Microservices", "SQL"],
            "experience_years": 7.0,
            "education": "Master of Science in Software Engineering",
            "category": "Engineering",
            "raw_text": "Sarah Jenkins\nLead .NET Cloud Solutions Architect\nsarah.jenkins@example.com | +1-555-0144 | New York, NY\n\nPROFESSIONAL SUMMARY\nAccomplished .NET and C# Cloud Architect with 7 years of hands-on experience designing distributed microservices with ASP.NET Core, Entity Framework, and Azure.\n\nWORK EXPERIENCE\nLead .NET Architect — FinTech Core Systems (2020 - Present)\n• Architected enterprise cloud banking platform using .NET Core, C#, and ASP.NET Core microservices.\n• Integrated Entity Framework Core with high-concurrency SQL Server, executing over 5,000 TPS.\n• Deployed containerized .NET applications on Azure Kubernetes Service (AKS) with automated CI/CD.\n\nSKILLS\n.NET, .NET Core, C#, ASP.NET, ASP.NET Core, Entity Framework, Microsoft Azure, SQL Server, Microservices, System Design.",
            "user_id": seeker_id,
            "created_at": datetime.utcnow(),
            "file_url": "http://example.com/resumes/res_stack_dotnet_01.pdf"
        },
        {
            "resume_id": "res_stack_python_01",
            "candidate_name": "David Kumar",
            "email": "david.kumar@example.com",
            "phone": "+1-555-0177",
            "skills": ["Python", "FastAPI", "PyTorch", "LangChain", "Transformers", "NLP", "Docker", "Pandas", "Scikit-learn"],
            "experience_years": 6.0,
            "education": "Master of Science in Artificial Intelligence",
            "category": "Data Science",
            "raw_text": "David Kumar\nSenior Python AI/ML Engineer\ndavid.kumar@example.com | +1-555-0177 | Austin, TX\n\nPROFESSIONAL SUMMARY\nSenior Machine Learning Engineer specializing in Python, FastAPI, neural language models, LangChain, and production AI system deployment.\n\nWORK EXPERIENCE\nSenior Machine Learning Engineer — CognitiveScale (2021 - Present)\n• Built high-performance asynchronous microservices using Python and FastAPI handling 10M+ daily requests.\n• Implemented LangChain RAG pipelines connected to Pinecone vector store, reducing hallucinations by 60%.\n• Fine-tuned transformer models using PyTorch and HuggingFace for specialized document extraction.\n\nSKILLS\nPython, FastAPI, PyTorch, LangChain, Transformers, NLP, Vector Search, Docker, Pandas, Scikit-learn.",
            "user_id": seeker_id,
            "created_at": datetime.utcnow(),
            "file_url": "http://example.com/resumes/res_stack_python_01.pdf"
        },
        {
            "resume_id": "res_stack_typescript_01",
            "candidate_name": "Elena Rostova",
            "email": "elena.rostova@example.com",
            "phone": "+1-555-0188",
            "skills": ["TypeScript", "React", "Next.js", "Node.js", "GraphQL", "Tailwind CSS", "CI/CD", "Jest"],
            "experience_years": 4.5,
            "education": "Bachelor of Science in Information Technology",
            "category": "Engineering",
            "raw_text": "Elena Rostova\nFull-Stack TypeScript & React Engineer\nelena.rostova@example.com | +1-555-0188 | Seattle, WA\n\nPROFESSIONAL SUMMARY\nEnd-to-end TypeScript engineer with 4.5+ years building state-of-the-art web applications using Next.js, React 19, Node.js, and GraphQL.\n\nWORK EXPERIENCE\nSenior Frontend/Fullstack Engineer — SaaSSphere (2022 - Present)\n• Developed responsive SaaS portals in Next.js and TypeScript, achieving 99+ Lighthouse performance scores.\n• Crafted type-safe GraphQL APIs and Node.js microservices with 100% strict TypeScript typing.\n• Implemented interactive 3D visualizers with Three.js and React Three Fiber.\n\nSKILLS\nTypeScript, React, Next.js, Node.js, GraphQL, Tailwind CSS, Jest, Webpack, Micro-frontends.",
            "user_id": seeker_id,
            "created_at": datetime.utcnow(),
            "file_url": "http://example.com/resumes/res_stack_typescript_01.pdf"
        }
    ]
    
    resumes_csv_path = "data/processed/resumes_clean.csv"
    if not os.path.exists(resumes_csv_path):
        logger.error(f"Processed resumes CSV not found at {resumes_csv_path}. Run prepare_dataset.py first.")
        return
        
    df_resumes = pd.read_csv(resumes_csv_path)
    # Seed top 20 resumes
    df_resumes_seed = df_resumes.head(20)
    
    seeded_resumes = list(tech_stack_resumes)

    # Embed benchmark resumes
    for br in tech_stack_resumes:
        emb_text = f"Candidate: {br['candidate_name']}\nEducation: {br['education']}\nExperience: {br['experience_years']} years\nCategory: {br['category']}\nSkills: {', '.join(br['skills'])}\nResume Details: {br['raw_text']}"
        try:
            vec = generate_embedding(emb_text)
            vector_payloads.append({
                "id": f"resume_{br['resume_id']}",
                "values": vec,
                "metadata": {
                    "type": "resume",
                    "resume_id": br["resume_id"],
                    "candidate_name": br["candidate_name"],
                    "skills": ", ".join(br["skills"]),
                    "text": emb_text[:1000]
                }
            })
        except Exception as e:
            logger.warning(f"Failed to generate embedding for benchmark resume {br['resume_id']}: {e}")
    
    for _, row in df_resumes_seed.iterrows():
        resume_id = str(row["resume_id"])
        skills = [s.strip() for s in str(row["skills"]).split(",") if s.strip()]
        
        resume_doc = {
            "resume_id": resume_id,
            "candidate_name": str(row["name"]),
            "email": str(row["email"]),
            "phone": str(row["phone"]),
            "skills": skills,
            "experience_years": float(row["experience_years"]) if not pd.isna(row["experience_years"]) else 0.0,
            "education": str(row["education"]),
            "category": str(row["category"]),
            "raw_text": str(row["raw_text"]),
            "user_id": seeker_id,
            "created_at": datetime.utcnow(),
            "file_url": f"http://example.com/resumes/{resume_id}.pdf"
        }
        seeded_resumes.append(resume_doc)
        
        # Build embedding text
        emb_text = f"Candidate: {resume_doc['candidate_name']}\nEducation: {resume_doc['education']}\nExperience: {resume_doc['experience_years']} years\nCategory: {resume_doc['category']}\nSkills: {', '.join(resume_doc['skills'])}\nResume Details: {resume_doc['raw_text']}"
        try:
            vec = generate_embedding(emb_text)
            vector_payloads.append({
                "id": f"resume_{resume_id}",
                "values": vec,
                "metadata": {
                    "type": "resume",
                    "resume_id": resume_id,
                    "candidate_name": resume_doc["candidate_name"],
                    "skills": ", ".join(resume_doc["skills"]),
                    "text": emb_text[:1000]
                }
            })
        except Exception as e:
            logger.warning(f"Failed to generate embedding for resume {resume_id}: {e}")
            
    resumes_col.insert_many(seeded_resumes)
    logger.info(f"Seeded {len(seeded_resumes)} resumes to MongoDB.")
    
    # 4. Upsert Vectors to Pinecone
    if vector_payloads:
        logger.info("Upserting vectors to Pinecone Index...")
        try:
            upsert_batch(vector_payloads)
            logger.info(f"Successfully upserted {len(vector_payloads)} vectors to Pinecone.")
        except Exception as e:
            logger.error(f"Failed to upsert to Pinecone: {e}")
            
    logger.info("Database seeding successfully completed!")


def _seed_local_memory_fallback():
    from backend.services.rag_vector_store import upsert_rag_documents

    benchmark_docs = [
        {
            "id": "job_stack_mern_01",
            "text": "Job Title: Senior MERN Stack Engineer\nCompany: Nexus Web Systems\nCategory: Engineering\nLocation: San Francisco, CA (Remote)\nRequired Skills: MERN, MongoDB, Express, React, Node.js, TypeScript, REST, Docker\nDescription: Architect and maintain high-performance web applications using MERN (MongoDB, Express, React, Node.js) with TypeScript.",
            "metadata": {
                "type": "job",
                "job_id": "job_stack_mern_01",
                "title": "Senior MERN Stack Engineer",
                "company": "Nexus Web Systems",
                "category": "Engineering",
                "skills": "MERN, MongoDB, Express, React, Node.js, TypeScript, REST, Docker",
            }
        },
        {
            "id": "job_stack_dotnet_01",
            "text": "Job Title: Principal .NET / C# Cloud Architect\nCompany: Enterprise Global FinTech\nCategory: Engineering\nLocation: New York, NY (Hybrid)\nRequired Skills: .NET, .NET Core, C#, ASP.NET Core, Entity Framework, Azure, Microservices, SQL\nDescription: Lead enterprise microservices architecture using modern .NET 8 / ASP.NET Core and C#.",
            "metadata": {
                "type": "job",
                "job_id": "job_stack_dotnet_01",
                "title": "Principal .NET / C# Cloud Architect",
                "company": "Enterprise Global FinTech",
                "category": "Engineering",
                "skills": ".NET, .NET Core, C#, ASP.NET Core, Entity Framework, Azure, Microservices, SQL",
            }
        },
        {
            "id": "job_stack_python_01",
            "text": "Job Title: Lead Python & AI Systems Engineer\nCompany: Cognitive AI Labs\nCategory: Data Science\nLocation: Austin, TX (Remote)\nRequired Skills: Python, FastAPI, PyTorch, LangChain, Transformers, Docker, Pinecone, NLP\nDescription: Design and productionize neural AI systems using Python and FastAPI with LangChain RAG pipelines.",
            "metadata": {
                "type": "job",
                "job_id": "job_stack_python_01",
                "title": "Lead Python & AI Systems Engineer",
                "company": "Cognitive AI Labs",
                "category": "Data Science",
                "skills": "Python, FastAPI, PyTorch, LangChain, Transformers, Docker, Pinecone, NLP",
            }
        },
        {
            "id": "job_stack_typescript_01",
            "text": "Job Title: Senior Full-Stack TypeScript Engineer\nCompany: ModernScale Platform\nCategory: Engineering\nLocation: Seattle, WA (Remote)\nRequired Skills: TypeScript, React, Next.js, Node.js, GraphQL, Tailwind CSS, CI/CD\nDescription: Spearhead end-to-end fullstack development in pure TypeScript across Next.js React frontend and Node.js backend.",
            "metadata": {
                "type": "job",
                "job_id": "job_stack_typescript_01",
                "title": "Senior Full-Stack TypeScript Engineer",
                "company": "ModernScale Platform",
                "category": "Engineering",
                "skills": "TypeScript, React, Next.js, Node.js, GraphQL, Tailwind CSS, CI/CD",
            }
        },
    ]

    jobs_csv_path = "data/processed/jobs_clean.csv"
    if not os.path.exists(jobs_csv_path):
        if benchmark_docs:
            upsert_rag_documents(benchmark_docs)
            logger.info("Seeded benchmark tech stack jobs to RAG vector store.")
        return

    try:
        df_jobs = pd.read_csv(jobs_csv_path).head(100)
        docs = list(benchmark_docs)
        for _, row in df_jobs.iterrows():
            job_id = str(row["job_id"])
            req_skills = [s.strip() for s in str(row["required_skills"]).split(",") if s.strip()]
            emb_text = f"Job Title: {row['title']}\nCompany: {row['company']}\nCategory: {row['category']}\nLocation: {row['location']}\nRequired Skills: {', '.join(req_skills)}\nDescription: {row['description']}"
            docs.append({
                "id": f"job_{job_id}",
                "text": emb_text,
                "metadata": {
                    "type": "job",
                    "job_id": job_id,
                    "title": str(row["title"]),
                    "company": str(row["company"]),
                    "category": str(row["category"]),
                    "skills": ", ".join(req_skills),
                }
            })
        upsert_rag_documents(docs)
        logger.info(f"Successfully seeded {len(docs)} jobs into RAG vector store!")
    except Exception as e:
        logger.error(f"Failed to run local vector store fallback seed: {e}")


if __name__ == "__main__":
    seed()
