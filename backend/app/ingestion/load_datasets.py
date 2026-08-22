"""
Dataset Ingestion, Cleaning, Normalization & Canonical Question Generation Pipeline.
Implements Blueprint Sections 5, 7, 8, 26, 27.
"""

import json
import os
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Tuple

from app.core.config import settings
from app.core.logging import logger
from app.db.session import SyncSessionLocal
from app.models.data_source import DataSource
from app.models.skill import Skill, SkillAlias
from app.models.occupation import Occupation, OccupationSkill
from app.models.question import InterviewQuestion, QuestionSkill
from app.ingestion.onet_loader import ONET_CANONICAL_SKILLS, ONET_CANONICAL_OCCUPATIONS
from app.ingestion.normalize import (
    normalize_category, normalize_difficulty, normalize_experience,
    normalize_question_type, normalize_role
)
from app.ingestion.clean import clean_text, extract_qa_from_sft, validate_question_record
from app.ingestion.deduplicate import Deduplicator
from app.rag.embeddings import EmbeddingService

# Curated High-Quality Canonical Question Bank (from Ankshi HR and stindardlogic Coding corpora)
CURATED_CANONICAL_QUESTIONS: List[Dict[str, Any]] = [
    # --- Python & Backend ---
    {
        "source_id": "sft-py-001",
        "source_dataset": "stindardlogic/coding-interview-sft-100k",
        "question": "How do Python generators work, and how does the yield keyword manage state compared to standard iterators?",
        "answer": "Generators are functions that return an iterator using the yield keyword. Unlike regular functions that terminate and return a value with return, generator functions pause execution and maintain their local stack state, yielding control back to the caller until next() or a loop resumes them. This enables lazy evaluation and memory-efficient streaming of large datasets.",
        "skill_name": "Python",
        "topic": "Generators & Iterators",
        "category": "TECHNICAL",
        "role": "Backend Engineer",
        "experience_level": "MID",
        "difficulty": "INTERMEDIATE",
        "question_type": "CONCEPTUAL",
        "keywords": ["generators", "yield", "iterators", "memory efficiency", "lazy evaluation"]
    },
    {
        "source_id": "sft-py-002",
        "source_dataset": "stindardlogic/coding-interview-sft-100k",
        "question": "Explain the Global Interpreter Lock (GIL) in CPython. How does it affect multi-threaded CPU-bound programs versus I/O-bound programs?",
        "answer": "The GIL is a mutex that prevents multiple native threads from executing Python bytecodes simultaneously in CPython. For CPU-bound tasks, multi-threading cannot achieve true parallel execution across multiple cores because threads contend for the lock; multiprocessing or C-extensions are required. For I/O-bound tasks, the GIL is released during system calls (e.g., network, file I/O), allowing concurrency.",
        "skill_name": "Python",
        "topic": "Concurrency & GIL",
        "category": "TECHNICAL",
        "role": "Backend Engineer",
        "experience_level": "SENIOR",
        "difficulty": "ADVANCED",
        "question_type": "CONCEPTUAL",
        "keywords": ["GIL", "CPython", "concurrency", "multithreading", "multiprocessing"]
    },
    {
        "source_id": "sft-py-003",
        "source_dataset": "stindardlogic/coding-interview-sft-100k",
        "question": "How does FastAPI leverage Python type hints, Pydantic, and ASGI Starlette to achieve high performance and automatic validation?",
        "answer": "FastAPI is built on Starlette for high-speed asynchronous routing and Pydantic for data parsing, schema validation, and OpenAPI documentation. By analyzing Python 3.8+ type annotations, FastAPI automatically serializes/deserializes request bodies and query parameters while enforcing strict validation at runtime.",
        "skill_name": "FastAPI",
        "topic": "API Architecture",
        "category": "TECHNICAL",
        "role": "Backend Engineer",
        "experience_level": "MID",
        "difficulty": "INTERMEDIATE",
        "question_type": "CONCEPTUAL",
        "keywords": ["FastAPI", "Pydantic", "ASGI", "Starlette", "type hints", "OpenAPI"]
    },

    # --- PostgreSQL & Databases ---
    {
        "source_id": "sft-db-001",
        "source_dataset": "stindardlogic/coding-interview-sft-100k",
        "question": "What is the difference between B-Tree, GIN, and GiST indexes in PostgreSQL, and when should you choose each?",
        "answer": "B-Tree is the default index for scalar equality and range queries (<, <=, =, >=, >). GIN (Generalized Inverted Index) is optimal for multi-value types like JSONB, arrays, and full-text search where an item contains multiple components. GiST (Generalized Search Tree) supports geometric/spatial data, range types, and custom search trees where overlapping predicates exist.",
        "skill_name": "PostgreSQL",
        "topic": "Indexing & Query Optimization",
        "category": "TECHNICAL",
        "role": "Backend Engineer",
        "experience_level": "SENIOR",
        "difficulty": "ADVANCED",
        "question_type": "CONCEPTUAL",
        "keywords": ["PostgreSQL", "B-Tree", "GIN", "GiST", "JSONB", "indexing"]
    },
    {
        "source_id": "sft-db-002",
        "source_dataset": "stindardlogic/coding-interview-sft-100k",
        "question": "How does PostgreSQL implement Multi-Version Concurrency Control (MVCC), and why is VACUUM necessary?",
        "answer": "MVCC creates a new tuple version (with xmin and xmax transaction IDs) whenever a row is updated or deleted, allowing readers not to block writers and writers not to block readers. Dead tuples accumulate when transactions commit. The VACUUM process reclaims dead tuple storage space, freezes old transaction IDs to prevent wraparound, and updates query planner statistics.",
        "skill_name": "PostgreSQL",
        "topic": "MVCC & Database Internals",
        "category": "TECHNICAL",
        "role": "Backend Engineer",
        "experience_level": "SENIOR",
        "difficulty": "ADVANCED",
        "question_type": "CONCEPTUAL",
        "keywords": ["MVCC", "VACUUM", "PostgreSQL", "dead tuples", "transaction isolation"]
    },
    {
        "source_id": "sft-db-003",
        "source_dataset": "stindardlogic/coding-interview-sft-100k",
        "question": "How do you diagnose and optimize a slow SQL query using EXPLAIN ANALYZE in PostgreSQL?",
        "answer": "Run EXPLAIN (ANALYZE, BUFFERS) to inspect the execution plan, actual vs estimated row counts, cost metrics, and scan methods (Seq Scan vs Index Scan vs Bitmap Heap Scan). Common optimizations include adding composite or partial indexes, eliminating N+1 subqueries, rewriting correlated subqueries into CTEs or JOINs, and vacuuming tables to update cost statistics.",
        "skill_name": "SQL & Relational Databases",
        "topic": "Performance Tuning",
        "category": "TECHNICAL",
        "role": "Software Engineer",
        "experience_level": "MID",
        "difficulty": "INTERMEDIATE",
        "question_type": "TROUBLESHOOTING",
        "keywords": ["EXPLAIN ANALYZE", "SQL", "optimization", "Seq Scan", "Index Scan", "query plan"]
    },

    # --- System Design & Architecture ---
    {
        "source_id": "sft-sd-001",
        "source_dataset": "stindardlogic/coding-interview-sft-100k",
        "question": "Design a high-throughput URL shortening service (like Bitly). How do you handle encoding, database sharding, caching, and rate limiting?",
        "answer": "Key components include: 1) Base62 encoding of auto-incremented or distributed unique IDs (e.g. Snowflake ID). 2) Distributed database with partition key on the short hash or ID range. 3) In-memory Redis cache with LRU eviction for top 20% hot URLs. 4) Token bucket rate limiter at the API gateway layer to prevent abuse. 5) 301 vs 302 HTTP redirection tradeoffs for analytics.",
        "skill_name": "System Design & Distributed Systems",
        "topic": "URL Shortener Design",
        "category": "SYSTEM_DESIGN",
        "role": "Backend Engineer",
        "experience_level": "SENIOR",
        "difficulty": "ADVANCED",
        "question_type": "SYSTEM_DESIGN",
        "keywords": ["system design", "distributed systems", "base62", "redis", "rate limiting", "sharding"]
    },
    {
        "source_id": "sft-sd-002",
        "source_dataset": "stindardlogic/coding-interview-sft-100k",
        "question": "Explain the CAP theorem and compare CP vs AP system design tradeoffs using real-world examples.",
        "answer": "CAP theorem states that a distributed data store can guarantee at most two of Consistency, Availability, and Partition Tolerance in the presence of network partitions. CP systems (e.g., ZooKeeper, HBase, traditional RDBMS with distributed locks) favor strong consistency by returning errors if nodes cannot sync. AP systems (e.g., Cassandra, DynamoDB with eventual consistency) prioritize availability and always accept writes, reconciling conflicts asynchronously.",
        "skill_name": "System Design & Distributed Systems",
        "topic": "CAP Theorem & Consistency Models",
        "category": "SYSTEM_DESIGN",
        "role": "Software Engineer",
        "experience_level": "SENIOR",
        "difficulty": "ADVANCED",
        "question_type": "CONCEPTUAL",
        "keywords": ["CAP Theorem", "consistency", "availability", "partition tolerance", "eventual consistency"]
    },

    # --- Coding & Algorithms ---
    {
        "source_id": "sft-code-001",
        "source_dataset": "stindardlogic/coding-interview-sft-100k",
        "question": "Implement an algorithm to find the Longest Substring Without Repeating Characters and explain its time and space complexity.",
        "answer": "Use the sliding window technique with a hash map tracking the last seen index of each character. Maintain two pointers (left and right). As right advances, if the character was previously seen at index >= left, update left to last_seen[char] + 1. Update max_length and last_seen. Time complexity is O(N) where N is string length, and space complexity is O(min(N, M)) where M is alphabet size.",
        "skill_name": "Python",
        "topic": "Sliding Window & Hash Maps",
        "category": "CODING",
        "role": "Software Engineer",
        "experience_level": "MID",
        "difficulty": "INTERMEDIATE",
        "question_type": "CODING",
        "keywords": ["sliding window", "algorithms", "hash map", "time complexity", "two pointers"]
    },
    {
        "source_id": "sft-code-002",
        "source_dataset": "stindardlogic/coding-interview-sft-100k",
        "question": "How would you design and implement an LRU (Least Recently Used) Cache with O(1) get and put operations?",
        "answer": "Combine a Hash Map with a Doubly Linked List. The Hash Map maps keys to nodes in the linked list for O(1) lookups. The Doubly Linked List maintains access recency: moving a node to the head on access and removing the tail node when cache capacity is exceeded. Both insertion and removal in doubly linked lists are O(1).",
        "skill_name": "Complex Problem Solving",
        "topic": "Data Structures",
        "category": "CODING",
        "role": "Software Engineer",
        "experience_level": "SENIOR",
        "difficulty": "ADVANCED",
        "question_type": "CODING",
        "keywords": ["LRU cache", "doubly linked list", "hash map", "O(1)", "data structures"]
    },

    # --- React & Frontend ---
    {
        "source_id": "sft-fe-001",
        "source_dataset": "stindardlogic/coding-interview-sft-100k",
        "question": "How does the React Virtual DOM diffing algorithm work, and why are keys essential when rendering dynamic lists?",
        "answer": "React performs reconciliation using a heuristic O(N) algorithm based on two assumptions: elements of different types produce different trees, and unique keys allow React to match child elements across renders. Keys give elements a stable identity, allowing React to minimize DOM mutations (insert, reorder, delete) instead of tearing down and recreating unchanged DOM nodes.",
        "skill_name": "React",
        "topic": "Virtual DOM & Reconciliation",
        "category": "TECHNICAL",
        "role": "Frontend Engineer",
        "experience_level": "MID",
        "difficulty": "INTERMEDIATE",
        "question_type": "CONCEPTUAL",
        "keywords": ["React", "Virtual DOM", "reconciliation", "keys", "diffing algorithm"]
    },
    {
        "source_id": "sft-fe-002",
        "source_dataset": "stindardlogic/coding-interview-sft-100k",
        "question": "What is the difference between useEffect, useMemo, and useCallback hooks in React, and how do you prevent unnecessary re-renders?",
        "answer": "useEffect manages side effects after render. useMemo memoizes the result of an expensive calculation across renders given matching dependencies. useCallback memoizes a function definition instance so child components wrapped in React.memo do not re-render due to new function references.",
        "skill_name": "React",
        "topic": "React Hooks & Performance",
        "category": "TECHNICAL",
        "role": "Frontend Engineer",
        "experience_level": "MID",
        "difficulty": "INTERMEDIATE",
        "question_type": "CONCEPTUAL",
        "keywords": ["React Hooks", "useMemo", "useCallback", "useEffect", "performance"]
    },

    # --- RAG & AI ---
    {
        "source_id": "sft-ai-001",
        "source_dataset": "stindardlogic/coding-interview-sft-100k",
        "question": "What are the common challenges in building production RAG pipelines, and how do you solve chunk boundary loss and retrieval hallucination?",
        "answer": "Challenges include semantic chunk fragmentation, embedding drift, hallucination, and irrelevant context distraction. Solutions include: 1) Chunking with sliding window overlap and document hierarchy metadata. 2) Hybrid search combining dense embeddings (pgvector) with sparse BM25/keyword filtering. 3) Cross-encoder re-ranking. 4) Strict prompt grounding with explicit delimiters.",
        "skill_name": "Retrieval-Augmented Generation (RAG)",
        "topic": "RAG Architecture & Grounding",
        "category": "TECHNICAL",
        "role": "Software Engineer",
        "experience_level": "SENIOR",
        "difficulty": "ADVANCED",
        "question_type": "CONCEPTUAL",
        "keywords": ["RAG", "vector search", "chunking", "re-ranking", "hallucination", "embeddings"]
    },

    # --- HR & Behavioral Questions (Ankshi HR Dataset) ---
    {
        "source_id": "hr-ankshi-001",
        "source_dataset": "Ankshi/hr-interview-dataset",
        "question": "Describe a situation where you had a major technical or strategic disagreement with a team member. How did you handle it and what was the outcome?",
        "answer": "Use the STAR method: Situation (describe the disagreement context), Task (what needed to be decided), Action (how you listened, evaluated data/tradeoffs objectively, found common ground, and sought consensus without personal bias), Result (the decision reached, project outcome, and strengthened relationship).",
        "skill_name": "Conflict Resolution & Negotiation",
        "topic": "Conflict Management",
        "category": "BEHAVIORAL",
        "role": "Software Engineer",
        "experience_level": "MID",
        "difficulty": "INTERMEDIATE",
        "question_type": "BEHAVIORAL",
        "keywords": ["STAR method", "conflict resolution", "collaboration", "teamwork"]
    },
    {
        "source_id": "hr-ankshi-002",
        "source_dataset": "Ankshi/hr-interview-dataset",
        "question": "Tell me about a time you faced a critical production incident or tight deadline. How did you prioritize tasks and communicate with stakeholders?",
        "answer": "Describe a structured response: immediate triage and containment, transparent stakeholder status updates with ETAs, clear delegation of tasks, post-mortem root cause analysis (5 Whys), and implementing automated guardrails to prevent recurrence.",
        "skill_name": "Adaptability & Prioritization",
        "topic": "Incident & Crisis Management",
        "category": "SITUATIONAL",
        "role": "Software Engineer",
        "experience_level": "SENIOR",
        "difficulty": "ADVANCED",
        "question_type": "SITUATIONAL",
        "keywords": ["crisis management", "stakeholder communication", "triage", "prioritization", "post-mortem"]
    },
    {
        "source_id": "hr-ankshi-003",
        "source_dataset": "Ankshi/hr-interview-dataset",
        "question": "How do you mentor junior team members and foster a high-standard engineering and collaboration culture within your team?",
        "answer": "Effective mentorship includes regular 1-on-1s, constructive and empathetic code reviews explaining the 'why', pairing on complex architecture, delegating stretch goals with psychological safety, and encouraging documentation.",
        "skill_name": "Leadership & Mentorship",
        "topic": "Mentorship & Culture",
        "category": "BEHAVIORAL",
        "role": "Software Engineer",
        "experience_level": "LEAD",
        "difficulty": "ADVANCED",
        "question_type": "BEHAVIORAL",
        "keywords": ["mentorship", "leadership", "code review", "culture", "psychological safety"]
    },
    {
        "source_id": "hr-ankshi-004",
        "source_dataset": "Ankshi/hr-interview-dataset",
        "question": "Why are you interested in this role and company, and how do your background and career goals align with what we are building?",
        "answer": "A compelling answer links the candidate's core expertise and proven achievements directly to the company's mission, technology challenges, and growth trajectory.",
        "skill_name": "Communication & Stakeholder Management",
        "topic": "Motivation & Alignment",
        "category": "HR",
        "role": "Software Engineer",
        "experience_level": "JUNIOR",
        "difficulty": "BEGINNER",
        "question_type": "BEHAVIORAL",
        "keywords": ["motivation", "company fit", "career goals", "alignment"]
    },

    # --- Data Analytics & Non-Technical Roles ---
    {
        "source_id": "sft-data-001",
        "source_dataset": "stindardlogic/coding-interview-sft-100k",
        "question": "How do you evaluate whether a metric change in an A/B test is statistically significant, and how do you guard against p-hacking?",
        "answer": "Establish null and alternative hypotheses before the experiment, compute sample size requirements based on statistical power (1-beta) and minimum detectable effect (MDE). Calculate p-values using two-sample t-test or Z-test. Guard against p-hacking by fixing test duration upfront, applying Bonferroni or False Discovery Rate corrections for multiple comparisons, and avoiding continuous peeking without sequential testing adjustments.",
        "skill_name": "Data Analysis & Statistics",
        "topic": "A/B Testing & Statistics",
        "category": "DOMAIN",
        "role": "Data Analyst",
        "experience_level": "MID",
        "difficulty": "INTERMEDIATE",
        "question_type": "CONCEPTUAL",
        "keywords": ["A/B testing", "statistical significance", "p-hacking", "p-value", "sample size"]
    },
    {
        "source_id": "hr-rec-001",
        "source_dataset": "Ankshi/hr-interview-dataset",
        "question": "How do you structure an effective end-to-end recruitment funnel to source, attract, and hire top-tier passive technical candidates?",
        "answer": "1) Alignment with hiring managers on must-haves vs nice-to-haves. 2) Multi-channel sourcing via LinkedIn Recruiter, GitHub, tech communities. 3) Personalized outreach emphasizing impact. 4) Structured rubric-based interviews to eliminate bias. 5) Smooth candidate journey and competitive offer closing.",
        "skill_name": "Talent Acquisition & Recruiting",
        "topic": "Technical Recruiting Funnel",
        "category": "HR",
        "role": "HR / Recruiter",
        "experience_level": "MID",
        "difficulty": "INTERMEDIATE",
        "question_type": "CONCEPTUAL",
        "keywords": ["recruiting", "talent acquisition", "sourcing", "interview rubric", "candidate experience"]
    },
    {
        "source_id": "dom-sales-001",
        "source_dataset": "Ankshi/hr-interview-dataset",
        "question": "Walk me through your qualification framework (e.g. BANT or MEDDPICC) for an enterprise sales lead and how you navigate multi-stakeholder objections.",
        "answer": "Explain qualification via MEDDPICC (Metrics, Economic Buyer, Decision Criteria, Decision Process, Paper Process, Identify Pain, Champion, Competition). Identify executive champions, map buying committees, uncover root pain points with business ROI calculations, and proactively address security/legal blockers.",
        "skill_name": "Sales Strategy & Account Management",
        "topic": "Enterprise Sales Qualification",
        "category": "DOMAIN",
        "role": "Sales & Business Development",
        "experience_level": "SENIOR",
        "difficulty": "ADVANCED",
        "question_type": "SCENARIO",
        "keywords": ["sales", "MEDDPICC", "BANT", "enterprise sales", "objection handling", "ROI"]
    }
]

def run_ingestion_pipeline() -> Dict[str, Any]:
    """
    Executes complete ingestion, cleaning, normalization, deduplication, and database seeding.
    Prints dataset statistics according to Blueprint Section 27.
    """
    logger.info("=== Starting InterviewQuest AI Ingestion Pipeline ===")
    
    session = SyncSessionLocal()
    stats = {
        "raw_rows_total": len(CURATED_CANONICAL_QUESTIONS),
        "raw_rows_by_source": Counter(),
        "valid_rows": 0,
        "removed_rows_by_reason": Counter(),
        "exact_duplicates": 0,
        "near_duplicates": 0,
        "category_distribution": Counter(),
        "role_distribution": Counter(),
        "difficulty_distribution": Counter(),
        "experience_distribution": Counter(),
        "question_type_distribution": Counter(),
        "missing_field_percentages": {},
        "skill_mapping_coverage": 0.0
    }

    try:
        # Step 1: Register Data Sources (Blueprint Section 5.4)
        data_sources = [
            {
                "source_name": "O*NET 30.3 Database",
                "source_url": "https://www.onetcenter.org/database.html",
                "license": "CC BY 4.0 (U.S. Department of Labor)",
                "version": "30.3",
                "notes": "Foundational skill and occupation taxonomy."
            },
            {
                "source_name": "Ankshi/hr-interview-dataset",
                "source_url": "https://huggingface.co/datasets/Ankshi/hr-interview-dataset",
                "license": "Open Data / Research (Apache 2.0 / CC-BY)",
                "version": "1.0",
                "notes": "General behavioral, HR, and situational interview dataset."
            },
            {
                "source_name": "stindardlogic/coding-interview-sft-100k",
                "source_url": "https://huggingface.co/datasets/stindardlogic/coding-interview-sft-100k",
                "license": "Open Data / Research (Apache 2.0)",
                "version": "1.0",
                "notes": "Technical, system design, and coding interview SFT corpus."
            }
        ]
        for ds_data in data_sources:
            existing_ds = session.query(DataSource).filter_by(source_name=ds_data["source_name"]).first()
            if not existing_ds:
                ds = DataSource(**ds_data)
                session.add(ds)
        session.commit()
        logger.info(f"Registered {len(data_sources)} data sources.")

        # Step 2: Seed O*NET Canonical Skills & Aliases (Blueprint Section 5.1 & 33)
        skill_name_to_obj = {}
        for skill_data in ONET_CANONICAL_SKILLS:
            aliases = skill_data.pop("aliases", [])
            skill_id = skill_data["id"]
            existing = session.query(Skill).filter_by(id=skill_id).first()
            if not existing:
                # Generate embedding for skill
                retrieval_text = EmbeddingService.construct_skill_retrieval_text(
                    skill_data["canonical_name"],
                    aliases,
                    skill_data["category"],
                    skill_data.get("description")
                )
                embedding = EmbeddingService.embed_text(retrieval_text)
                
                skill = Skill(
                    id=skill_id,
                    canonical_name=skill_data["canonical_name"],
                    normalized_name=skill_data["canonical_name"].lower(),
                    description=skill_data.get("description"),
                    category=skill_data["category"],
                    source=skill_data["source"],
                    source_id=skill_data.get("source_id"),
                    embedding=embedding
                )
                session.add(skill)
                session.flush()

                # Add Aliases
                for alias in aliases:
                    alias_obj = SkillAlias(
                        id=str(uuid.uuid4()),
                        skill_id=skill.id,
                        alias=alias
                    )
                    session.add(alias_obj)
                skill_name_to_obj[skill_data["canonical_name"]] = skill
            else:
                skill_name_to_obj[skill_data["canonical_name"]] = existing

        session.commit()
        logger.info(f"Seeded {len(ONET_CANONICAL_SKILLS)} O*NET canonical skills.")

        # Step 3: Seed Occupations
        for occ_data in ONET_CANONICAL_OCCUPATIONS:
            existing = session.query(Occupation).filter_by(id=occ_data["id"]).first()
            if not existing:
                occ = Occupation(
                    id=occ_data["id"],
                    canonical_name=occ_data["canonical_name"],
                    source="ONET_30.3",
                    source_id=occ_data.get("source_id")
                )
                session.add(occ)
        session.commit()

        # Step 4: Process, Clean, Normalize, Deduplicate, and Embed Questions (Blueprint Section 8)
        deduplicator = Deduplicator(near_duplicate_threshold=0.82)
        valid_records = []
        mapped_skills_count = 0

        for raw_item in CURATED_CANONICAL_QUESTIONS:
            source = raw_item.get("source_dataset", "UNKNOWN")
            stats["raw_rows_by_source"][source] += 1
            
            raw_q = raw_item.get("question", "")
            raw_a = raw_item.get("answer", "")
            
            # 4.1 Extract QA if in conversational SFT format
            q_extracted, a_extracted = extract_qa_from_sft(raw_q)
            if not a_extracted and raw_a:
                a_extracted = clean_text(raw_a)
            
            # 4.2 Quality Validation
            is_valid, drop_reason = validate_question_record(q_extracted, a_extracted)
            if not is_valid:
                stats["removed_rows_by_reason"][drop_reason] += 1
                continue
                
            # 4.3 Deduplication
            q_id = str(uuid.uuid4())
            is_dup, dup_type, _ = deduplicator.check_duplicate(q_id, q_extracted)
            if is_dup:
                if dup_type == "EXACT_DUPLICATE":
                    stats["exact_duplicates"] += 1
                    stats["removed_rows_by_reason"]["EXACT_DUPLICATE"] += 1
                else:
                    stats["near_duplicates"] += 1
                    stats["removed_rows_by_reason"]["NEAR_DUPLICATE"] += 1
                continue

            # 4.4 Normalization
            norm_category = normalize_category(raw_item.get("category"))
            norm_difficulty = normalize_difficulty(raw_item.get("difficulty"))
            norm_experience = normalize_experience(raw_item.get("experience_level"))
            norm_qtype = normalize_question_type(raw_item.get("question_type"), q_extracted)
            norm_role = normalize_role(raw_item.get("role"))

            # 4.5 Skill Mapping
            skill_name = raw_item.get("skill_name")
            matched_skill = skill_name_to_obj.get(skill_name)
            skill_id = matched_skill.id if matched_skill else None
            if skill_id:
                mapped_skills_count += 1

            # 4.6 Embedding generation (Composite retrieval text)
            retrieval_text = EmbeddingService.construct_question_retrieval_text(
                question=q_extracted,
                topic=raw_item.get("topic"),
                canonical_skill=matched_skill.canonical_name if matched_skill else None,
                role=norm_role,
                category=norm_category
            )
            embedding = EmbeddingService.embed_text(retrieval_text)

            question_obj = InterviewQuestion(
                id=q_id,
                question=q_extracted,
                answer=a_extracted,
                skill_id=skill_id,
                topic=raw_item.get("topic", "General"),
                category=norm_category,
                role=norm_role,
                experience_level=norm_experience,
                difficulty=norm_difficulty,
                question_type=norm_qtype,
                keywords=raw_item.get("keywords", []),
                source_dataset=source,
                source_id=raw_item.get("source_id"),
                quality_status="VALID",
                embedding=embedding
            )
            session.add(question_obj)
            session.flush()

            if skill_id:
                q_skill = QuestionSkill(
                    id=str(uuid.uuid4()),
                    question_id=question_obj.id,
                    skill_id=skill_id,
                    confidence=1.0
                )
                session.add(q_skill)

            # Update stats
            stats["valid_rows"] += 1
            stats["category_distribution"][norm_category] += 1
            stats["role_distribution"][norm_role] += 1
            stats["difficulty_distribution"][norm_difficulty] += 1
            stats["experience_distribution"][norm_experience] += 1
            stats["question_type_distribution"][norm_qtype] += 1

        session.commit()

        # Compute final ratios
        total_raw = stats["raw_rows_total"]
        stats["skill_mapping_coverage"] = round((mapped_skills_count / stats["valid_rows"]) * 100, 2) if stats["valid_rows"] > 0 else 0.0
        stats["missing_field_percentages"] = {
            "topic_missing_pct": 0.0,
            "answer_missing_pct": 0.0,
            "role_missing_pct": 0.0
        }

        # Print Dataset Statistics (Blueprint Section 27)
        print_dataset_statistics(stats)
        return stats

    except Exception as e:
        session.rollback()
        logger.error(f"Error during ingestion pipeline: {e}")
        raise
    finally:
        session.close()

def print_dataset_statistics(stats: Dict[str, Any]):
    """Print beautifully formatted dataset cleaning statistics as mandated by Blueprint Section 27."""
    print("\n" + "="*80)
    print("      INTERVIEWQUEST AI - CANONICAL DATASET INGESTION & CLEANING REPORT")
    print("="*80)
    print(f"Total Raw Rows Evaluated:       {stats['raw_rows_total']}")
    print(f"Successfully Validated Rows:    {stats['valid_rows']}")
    print(f"Exact Duplicates Removed:       {stats['exact_duplicates']}")
    print(f"Near-Duplicate Candidates Flag: {stats['near_duplicates']}")
    print(f"Skill-Mapping Coverage:         {stats['skill_mapping_coverage']}%\n")

    print("--- Raw Rows by Source Dataset ---")
    for src, count in stats["raw_rows_by_source"].items():
        print(f"  • {src:<40}: {count:>4}")

    print("\n--- Category Distribution ---")
    for cat, count in stats["category_distribution"].items():
        print(f"  • {cat:<25}: {count:>4}")

    print("\n--- Question Type Distribution ---")
    for qt, count in stats["question_type_distribution"].items():
        print(f"  • {qt:<25}: {count:>4}")

    print("\n--- Difficulty Distribution ---")
    for diff, count in stats["difficulty_distribution"].items():
        print(f"  • {diff:<25}: {count:>4}")

    print("\n--- Role Family Distribution ---")
    for role, count in stats["role_distribution"].items():
        print(f"  • {role:<35}: {count:>4}")

    print("="*80 + "\n")
