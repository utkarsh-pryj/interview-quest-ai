"""
O*NET 30.3 Knowledge Base Loader.
Provides canonical skills, software tools, essential/transferable skills, occupations, and alias mappings.
Conforms to Blueprint Section 5.1 & 33.
"""

from typing import List, Dict, Any

# Curated high-fidelity O*NET 30.3 Skill Taxonomy
ONET_CANONICAL_SKILLS: List[Dict[str, Any]] = [
    # --- Backend & Languages ---
    {
        "id": "onet-skill-python",
        "canonical_name": "Python",
        "category": "TECHNICAL",
        "description": "General-purpose programming language for backend development, data analysis, automation, and AI.",
        "source": "ONET_30.3",
        "source_id": "15-1252.00-PY",
        "aliases": ["Python", "Python 3", "Py", "CPython", "Pythonic", "Asyncio"]
    },
    {
        "id": "onet-skill-javascript",
        "canonical_name": "JavaScript",
        "category": "TECHNICAL",
        "description": "High-level programming language used for web frontend and Node.js backend development.",
        "source": "ONET_30.3",
        "source_id": "15-1254.00-JS",
        "aliases": ["JavaScript", "JS", "ES6", "ECMAScript", "Modern JavaScript", "Vanilla JS"]
    },
    {
        "id": "onet-skill-typescript",
        "canonical_name": "TypeScript",
        "category": "TECHNICAL",
        "description": "Statically typed superset of JavaScript providing compile-time type checking.",
        "source": "ONET_30.3",
        "source_id": "15-1254.00-TS",
        "aliases": ["TypeScript", "TS", "Type Script"]
    },
    {
        "id": "onet-skill-java",
        "canonical_name": "Java",
        "category": "TECHNICAL",
        "description": "Object-oriented, class-based language widely used in enterprise backend systems and Android.",
        "source": "ONET_30.3",
        "source_id": "15-1252.00-JAVA",
        "aliases": ["Java", "Java 8", "Java 11", "Java 17", "Java 21", "JVM", "Core Java"]
    },
    {
        "id": "onet-skill-golang",
        "canonical_name": "Go (Golang)",
        "category": "TECHNICAL",
        "description": "Compiled, statically typed language designed at Google for concurrent, scalable backend microservices.",
        "source": "ONET_30.3",
        "source_id": "15-1252.00-GO",
        "aliases": ["Go", "Golang", "Go Language", "Goroutines"]
    },
    {
        "id": "onet-skill-cplusplus",
        "canonical_name": "C++",
        "category": "TECHNICAL",
        "description": "General-purpose programming language with low-level memory manipulation for high-performance systems.",
        "source": "ONET_30.3",
        "source_id": "15-1252.00-CPP",
        "aliases": ["C++", "CPP", "Modern C++", "C++17", "C++20"]
    },
    {
        "id": "onet-skill-csharp",
        "canonical_name": "C# (.NET)",
        "category": "TECHNICAL",
        "description": "Modern object-oriented programming language for .NET runtime developed by Microsoft.",
        "source": "ONET_30.3",
        "source_id": "15-1252.00-CS",
        "aliases": ["C#", "CSharp", ".NET", "ASP.NET", ".NET Core", "dot net"]
    },
    {
        "id": "onet-skill-rust",
        "canonical_name": "Rust",
        "category": "TECHNICAL",
        "description": "Systems programming language focused on safety, memory speed, and concurrency without a garbage collector.",
        "source": "ONET_30.3",
        "source_id": "15-1252.00-RUST",
        "aliases": ["Rust", "Rustlang", "Cargo"]
    },

    # --- Web Frameworks & Frontend ---
    {
        "id": "onet-skill-fastapi",
        "canonical_name": "FastAPI",
        "category": "TECHNICAL",
        "description": "Modern, fast, high-performance web framework for building APIs with Python 3.8+ based on standard Python type hints.",
        "source": "ONET_30.3",
        "source_id": "15-1254.00-FASTAPI",
        "aliases": ["FastAPI", "Fast API", "Starlette", "Pydantic API"]
    },
    {
        "id": "onet-skill-django",
        "canonical_name": "Django",
        "category": "TECHNICAL",
        "description": "High-level Python web framework that enables rapid development of secure and maintainable websites.",
        "source": "ONET_30.3",
        "source_id": "15-1254.00-DJANGO",
        "aliases": ["Django", "Django REST Framework", "DRF", "Django ORM"]
    },
    {
        "id": "onet-skill-react",
        "canonical_name": "React",
        "category": "TECHNICAL",
        "description": "Component-based JavaScript library for building interactive user interfaces.",
        "source": "ONET_30.3",
        "source_id": "15-1254.00-REACT",
        "aliases": ["React", "React.js", "ReactJS", "React Hooks", "Redux", "Next.js", "NextJS"]
    },
    {
        "id": "onet-skill-vue",
        "canonical_name": "Vue.js",
        "category": "TECHNICAL",
        "description": "Progressive JavaScript framework for building user interfaces and single-page applications.",
        "source": "ONET_30.3",
        "source_id": "15-1254.00-VUE",
        "aliases": ["Vue", "Vue.js", "VueJS", "Nuxt", "Nuxt.js"]
    },
    {
        "id": "onet-skill-nodejs",
        "canonical_name": "Node.js",
        "category": "TECHNICAL",
        "description": "Asynchronous event-driven JavaScript runtime built on Chrome's V8 JavaScript engine.",
        "source": "ONET_30.3",
        "source_id": "15-1254.00-NODE",
        "aliases": ["Node.js", "NodeJS", "Node", "Express", "Express.js", "NestJS"]
    },

    # --- Databases & Vector Search ---
    {
        "id": "onet-skill-postgresql",
        "canonical_name": "PostgreSQL",
        "category": "TECHNICAL",
        "description": "Powerful open source object-relational database system with advanced indexing, JSON support, and vector search.",
        "source": "ONET_30.3",
        "source_id": "15-1243.00-PG",
        "aliases": ["PostgreSQL", "Postgres", "psql", "pgvector", "PostgreSQL 15", "PostgreSQL 16", "PostgreSQL 18"]
    },
    {
        "id": "onet-skill-sql",
        "canonical_name": "SQL & Relational Databases",
        "category": "TECHNICAL",
        "description": "Domain-specific language used in programming and designed for managing data held in a relational database management system.",
        "source": "ONET_30.3",
        "source_id": "15-1243.00-SQL",
        "aliases": ["SQL", "Relational Database", "RDBMS", "MySQL", "Oracle SQL", "Query Optimization", "Database Normalization", "Indexing"]
    },
    {
        "id": "onet-skill-nosql",
        "canonical_name": "NoSQL Databases",
        "category": "TECHNICAL",
        "description": "Non-relational database management systems including document, key-value, column-family, and graph databases.",
        "source": "ONET_30.3",
        "source_id": "15-1243.00-NOSQL",
        "aliases": ["NoSQL", "MongoDB", "Cassandra", "DynamoDB", "Couchbase"]
    },
    {
        "id": "onet-skill-redis",
        "canonical_name": "Redis & Caching",
        "category": "TECHNICAL",
        "description": "In-memory data structure store used as a database, cache, streaming engine, and message broker.",
        "source": "ONET_30.3",
        "source_id": "15-1243.00-REDIS",
        "aliases": ["Redis", "Memcached", "Caching", "Cache Invalidation", "Distributed Cache"]
    },

    # --- System Architecture & Cloud & DevOps ---
    {
        "id": "onet-skill-system-design",
        "canonical_name": "System Design & Distributed Systems",
        "category": "SYSTEM_DESIGN",
        "description": "Architecting scalable, resilient distributed systems, load balancing, sharding, replication, and microservices.",
        "source": "ONET_30.3",
        "source_id": "15-1252.00-SYSDES",
        "aliases": ["System Design", "Distributed Systems", "High Level Design", "Scalability", "Microservices", "Load Balancing", "Sharding", "CAP Theorem"]
    },
    {
        "id": "onet-skill-docker",
        "canonical_name": "Docker & Containers",
        "category": "TECHNICAL",
        "description": "Platform for developing, shipping, and running applications in isolated containers.",
        "source": "ONET_30.3",
        "source_id": "15-1244.00-DOCKER",
        "aliases": ["Docker", "Containerization", "Containers", "Docker Compose", "Dockerfile"]
    },
    {
        "id": "onet-skill-kubernetes",
        "canonical_name": "Kubernetes",
        "category": "TECHNICAL",
        "description": "Automated deployment, scaling, and management of containerized applications.",
        "source": "ONET_30.3",
        "source_id": "15-1244.00-K8S",
        "aliases": ["Kubernetes", "K8s", "Helm", "Container Orchestration"]
    },
    {
        "id": "onet-skill-aws",
        "canonical_name": "Amazon Web Services (AWS)",
        "category": "TECHNICAL",
        "description": "Comprehensive cloud computing platform providing compute, storage, databases, and networking.",
        "source": "ONET_30.3",
        "source_id": "15-1244.00-AWS",
        "aliases": ["AWS", "Amazon Web Services", "EC2", "S3", "Lambda", "ECS", "CloudFormation"]
    },
    {
        "id": "onet-skill-cicd",
        "canonical_name": "CI/CD & DevOps",
        "category": "TECHNICAL",
        "description": "Continuous integration and continuous deployment pipelines for automated testing and zero-downtime releases.",
        "source": "ONET_30.3",
        "source_id": "15-1244.00-CICD",
        "aliases": ["CI/CD", "DevOps", "GitHub Actions", "GitLab CI", "Jenkins", "Continuous Integration", "Continuous Delivery"]
    },
    {
        "id": "onet-skill-git",
        "canonical_name": "Git & Version Control",
        "category": "TECHNICAL",
        "description": "Distributed version control system for tracking changes in source code during software development.",
        "source": "ONET_30.3",
        "source_id": "15-1252.00-GIT",
        "aliases": ["Git", "GitHub", "GitLab", "Version Control", "Pull Requests", "Branching"]
    },

    # --- AI, ML & RAG ---
    {
        "id": "onet-skill-rag",
        "canonical_name": "Retrieval-Augmented Generation (RAG)",
        "category": "TECHNICAL",
        "description": "Architecture combining external knowledge retrieval, semantic vector indexing, and LLM synthesis.",
        "source": "ONET_30.3",
        "source_id": "15-1221.00-RAG",
        "aliases": ["RAG", "Retrieval-Augmented Generation", "Vector Search", "Semantic Retrieval", "pgvector", "Hybrid Search", "Chunking", "Embeddings"]
    },
    {
        "id": "onet-skill-machine-learning",
        "canonical_name": "Machine Learning & NLP",
        "category": "TECHNICAL",
        "description": "Designing and evaluating supervised/unsupervised models, deep learning, NLP, and LLM applications.",
        "source": "ONET_30.3",
        "source_id": "15-1221.00-ML",
        "aliases": ["Machine Learning", "ML", "NLP", "Natural Language Processing", "PyTorch", "TensorFlow", "Scikit-Learn", "LLMs", "Hugging Face"]
    },

    # --- Data Analytics & BI ---
    {
        "id": "onet-skill-data-analysis",
        "canonical_name": "Data Analysis & Statistics",
        "category": "DOMAIN",
        "description": "Extracting insights from quantitative datasets, statistical hypothesis testing, and exploratory data analysis.",
        "source": "ONET_30.3",
        "source_id": "15-2051.00-DATA",
        "aliases": ["Data Analysis", "Statistics", "Pandas", "NumPy", "EDA", "A/B Testing", "Data Cleaning"]
    },
    {
        "id": "onet-skill-powerbi-tableau",
        "canonical_name": "BI & Data Visualization",
        "category": "DOMAIN",
        "description": "Building interactive dashboards and KPI reports using Power BI, Tableau, or Looker.",
        "source": "ONET_30.3",
        "source_id": "15-2051.00-BI",
        "aliases": ["Power BI", "Tableau", "Looker", "Data Visualization", "Dashboards", "Metabase", "Charts"]
    },

    # --- Essential, Behavioral & Situational Skills ---
    {
        "id": "onet-skill-problem-solving",
        "canonical_name": "Complex Problem Solving",
        "category": "BEHAVIORAL",
        "description": "Identifying complex problems and reviewing related information to develop and evaluate options and implement solutions.",
        "source": "ONET_30.3",
        "source_id": "2.A.2.a",
        "aliases": ["Problem Solving", "Troubleshooting", "Root Cause Analysis", "Analytical Thinking", "Critical Thinking", "Debugging"]
    },
    {
        "id": "onet-skill-communication",
        "canonical_name": "Communication & Stakeholder Management",
        "category": "BEHAVIORAL",
        "description": "Giving full attention to others, speaking clearly, translating technical concepts for business stakeholders, and active listening.",
        "source": "ONET_30.3",
        "source_id": "2.A.1.a",
        "aliases": ["Communication", "Stakeholder Management", "Active Listening", "Presentation", "Technical Writing", "Cross-Functional Collaboration"]
    },
    {
        "id": "onet-skill-leadership",
        "canonical_name": "Leadership & Mentorship",
        "category": "BEHAVIORAL",
        "description": "Guiding teams, mentoring junior engineers, driving engineering standards, and resolving workplace conflicts.",
        "source": "ONET_30.3",
        "source_id": "2.B.1.a",
        "aliases": ["Leadership", "Mentorship", "Team Management", "Coaching", "Strategic Planning", "Ownership"]
    },
    {
        "id": "onet-skill-conflict-resolution",
        "canonical_name": "Conflict Resolution & Negotiation",
        "category": "BEHAVIORAL",
        "description": "Bringing others together and trying to reconcile differences to align on common business goals.",
        "source": "ONET_30.3",
        "source_id": "2.B.1.b",
        "aliases": ["Conflict Resolution", "Negotiation", "Mediation", "Consensus Building", "Handling Disagreements"]
    },
    {
        "id": "onet-skill-adaptability",
        "canonical_name": "Adaptability & Prioritization",
        "category": "SITUATIONAL",
        "description": "Managing competing priorities, pivoting in fast-paced environments, and handling ambiguity.",
        "source": "ONET_30.3",
        "source_id": "2.B.2.i",
        "aliases": ["Adaptability", "Prioritization", "Agility", "Time Management", "Handling Ambiguity", "Multitasking"]
    },

    # --- Non-Technical Domain Skills (HR, Sales, Product) ---
    {
        "id": "onet-skill-recruiting",
        "canonical_name": "Talent Acquisition & Recruiting",
        "category": "HR",
        "description": "Sourcing candidates, interviewing, ATS pipeline management, candidate experience, and employer branding.",
        "source": "ONET_30.3",
        "source_id": "13-1071.00-REC",
        "aliases": ["Recruiting", "Talent Acquisition", "Sourcing", "Candidate Screening", "ATS", "Onboarding", "Job Posting"]
    },
    {
        "id": "onet-skill-sales-closing",
        "canonical_name": "Sales Strategy & Account Management",
        "category": "DOMAIN",
        "description": "Prospecting, lead qualification (BANT), consultative selling, client negotiations, and closing enterprise deals.",
        "source": "ONET_30.3",
        "source_id": "41-3091.00-SALES",
        "aliases": ["Sales", "Account Management", "B2B Sales", "Lead Generation", "Deal Closing", "Pipeline Management", "CRM", "Salesforce"]
    },
    {
        "id": "onet-skill-product-management",
        "canonical_name": "Product Strategy & Roadmapping",
        "category": "DOMAIN",
        "description": "User research, defining PRDs, feature prioritization, roadmapping, and driving product-market fit.",
        "source": "ONET_30.3",
        "source_id": "11-2021.00-PROD",
        "aliases": ["Product Management", "Product Strategy", "Roadmapping", "PRD", "User Stories", "Feature Prioritization", "Agile Product Owner"]
    }
]

# Canonical O*NET Occupations
ONET_CANONICAL_OCCUPATIONS: List[Dict[str, Any]] = [
    {"id": "onet-occ-swe", "canonical_name": "Software Developer / Engineer", "source_id": "15-1252.00"},
    {"id": "onet-occ-backend", "canonical_name": "Backend Software Engineer", "source_id": "15-1252.01"},
    {"id": "onet-occ-frontend", "canonical_name": "Frontend Web Developer", "source_id": "15-1254.00"},
    {"id": "onet-occ-fullstack", "canonical_name": "Full Stack Engineer", "source_id": "15-1252.02"},
    {"id": "onet-occ-devops", "canonical_name": "DevOps & Cloud Infrastructure Engineer", "source_id": "15-1244.00"},
    {"id": "onet-occ-data-analyst", "canonical_name": "Data Analyst & Business Intelligence Specialist", "source_id": "15-2051.00"},
    {"id": "onet-occ-data-scientist", "canonical_name": "Data Scientist & Machine Learning Engineer", "source_id": "15-1221.00"},
    {"id": "onet-occ-product-mgr", "canonical_name": "Technical Product Manager", "source_id": "11-2021.00"},
    {"id": "onet-occ-hr-recruiter", "canonical_name": "Human Resources & Talent Acquisition Specialist", "source_id": "13-1071.00"},
    {"id": "onet-occ-sales", "canonical_name": "Enterprise Sales & Business Development Representative", "source_id": "41-3091.00"}
]
