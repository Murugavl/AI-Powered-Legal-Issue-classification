# Satta Vizhi — Full Project Details Report

> **Purpose:** Raw, comprehensive extraction of all project information for later conversion into a structured presentation. Not formatted as slides – written as detailed paragraphs and structured points.

---

## 1. Basic Information

### Project Title
**Satta Vizhi** — AI-Powered Legal Issue Classification and Document Assistance Platform

*(The name "Satta Vizhi" is Tamil, loosely meaning "Eye of the Law" or "Legal Awareness")*

### Domain
This project spans multiple overlapping domains:
- **Artificial Intelligence / Natural Language Processing (NLP)** — using LLMs for conversation, classification, and document generation
- **Legal Technology (Legal Tech)** — digitising and automating the drafting of legal complaints and applications
- **Full-Stack Web Development** — a complete three-tier web application
- **Multilingual / Regional Language Technology** — supporting Indian regional languages such as Tamil, Hindi, Telugu, Kannada, Malayalam, Marathi, Bengali, and Gujarati

### Objective of the Project
The core objective of Satta Vizhi is to **dramatically lower the barrier for ordinary Indian citizens to access and exercise their legal rights**. Specifically, the system aims to:

1. Allow a layperson — even one with minimal literacy or no legal knowledge — to describe their problem in natural language (typed or spoken), in their preferred Indian language.
2. Automatically classify the legal issue into the correct category (theft, consumer complaint, cyber fraud, RTI application, salary dispute, etc.).
3. Conduct a structured, conversational interview to collect all necessary facts for the legal document.
4. Automatically generate a correctly formatted, professional legal complaint letter, petition, or application — in both the user's native language and in English — as a downloadable PDF.

The system is designed to serve as an AI-powered legal aid assistant that is accessible 24/7, requires no fees, and needs no prior legal knowledge from the user.

---

## 2. Problem Understanding

### The Exact Problem This Project Solves
In India, millions of people face legal grievances every year — theft, workplace exploitation, consumer fraud, cyber crime, property disputes, banking issues, and more. However, preparing even a simple police complaint or RTI application requires:

- Knowledge of which legal category the issue falls into
- Knowledge of which authority to approach (police station, consumer forum, court, government department)
- The ability to write a formally structured legal document in proper language
- Understanding of applicable sections of Indian law (IPC, IT Act, Consumer Protection Act, etc.)

Most citizens lack this knowledge entirely. They either give up, pay expensive lawyers for trivial filings, or turn to unqualified intermediaries who may exploit them.

### Who Faces This Problem
The problem is most acute for:
- **Low-income citizens** who cannot afford legal consultation fees
- **Rural and semi-urban populations** whose first language is a regional Indian language, not English
- **Senior citizens** unfamiliar with legal procedures
- **First-time complainants** who have never interacted with the legal system
- **Working-class individuals** who cannot afford the time to visit lawyers or courts repeatedly

### Why This Problem Is Important
India has over 1.4 billion people, with a legal system that is almost entirely English-language-centric at the formal documentation level. Legal literacy is extremely low. The gap between a citizen knowing they have been wronged and being able to act on it legally is enormous. This results in massive under-reporting of crimes and civil grievances. Satta Vizhi directly attacks this gap by placing a legal document preparation engine in the hands of every smartphone user.

---

## 3. Existing Solutions

### What Solutions Currently Exist
Several partial solutions exist:

1. **National Legal Services Authority (NALSA) and State Legal Services Authorities (SLSAs):** Provide free legal aid through human lawyers, but require physical presence at legal services centers. Availability is limited and the process can be slow.

2. **Vakil Search / LegalDesk / Lawyered.in:** Online legal platforms in India that provide legal consultation and document drafting services, but they are fee-based and operate in English only.

3. **e-Courts and Government Portals (eCourt, NCRB):** Allow digital filing in some jurisdictions, but require the pre-drafted document to be uploaded — they do not help the user draft it.

4. **Generic AI Chatbots (e.g., ChatGPT):** Can draft legal text when prompted correctly, but require the user to ask in English, know how to prompt correctly, and provide all facts themselves in a structured way. There is no guided interview, no language support, and no direct PDF output.

5. **Police e-FIR Portals:** Some states (Tamil Nadu, Delhi, UP) have partial online FIR filing portals, but they are limited to specific crime types, available only in English/Hindi, and not conversational.

### How Existing Solutions Work
Most existing paid platforms work by connecting users to a human legal professional who then drafts the document on their behalf. Government portals work as static forms that the user must fill in manually. Generic AI tools require the user to already know what they need and how to ask for it.

### Limitations and Drawbacks
- **No regional language support** in most platforms
- **Fee-based** access restricts use by economically weaker sections
- **No guided, conversational data collection** — the user must know what information to provide
- **Not accessible to low-literacy users** who struggle with form-based interfaces
- **No automatic legal classification** — the user must already know what kind of document to generate
- **No applicable Indian law reference** auto-included in documents
- **No bilingual output** — documents are either in English or a regional language, rarely both

---

## 4. Proposed Solution

### Detailed Explanation
Satta Vizhi is a three-tier web application with an AI brain at its centre. The solution works as follows:

A registered user logs into the web application using their mobile phone number. They navigate to the "New Case" section and are presented with a chat interface. They type — or speak, using the built-in voice input — a natural language description of their problem in any Indian language. The system's AI engine, built on LangGraph and powered by the Groq-hosted Llama 3.3 70B model, takes this description and does several things simultaneously:

1. **Language Detection:** Detects the ISO 639-1 language code of the input (Tamil, Hindi, English, Telugu, etc.) and sets this as the primary language for the entire session.
2. **Legal Classification:** Classifies the problem into one of 14 legal categories: Theft/Robbery, Assault, Cyber Crime, Consumer Complaint, Salary/Employment Dispute, Property Dispute, Landlord/Tenant Dispute, Harassment/Threat, Cheating/Fraud, Family/Matrimonial, Banking Issue, RTI Application, Insurance Dispute, or Other Civil Complaint.
3. **Safety Routing:** Evaluates whether the request is appropriate: if it represents an immediate life threat, it directs the user to emergency services (100, 112). If it requires complex litigation beyond document preparation, it refers them to a professional.
4. **Dynamic Interview Planning:** Generates a case-specific, 4-to-7-question interview plan tailored to the exact facts of the described problem. Unlike generic forms, the questions are dynamically generated for that specific situation.

The system then conducts a guided question-and-answer session, asking questions one at a time in the user's preferred language. At each turn, the LLM extracts the factual answer from the user's response (stripping conversational filler) and records it. After all questions are answered, the system presents a numbered confirmation summary and asks the user to confirm or correct any details. Upon confirmation, the bilingual document generator produces the legal document in both the user's language and in English, downloads it as a PDF with proper formatting.

### Core Idea and Workflow
The core architectural idea is a **stateful LangGraph workflow** with multiple nodes:
- [detect_language](file:///d:/Projects/AI-Powered-Legal-Issue-classification/nlp-python/graph.py#162-182) → [classify_and_plan](file:///d:/Projects/AI-Powered-Legal-Issue-classification/nlp-python/graph.py#221-646) → (if collecting) → [respond](file:///d:/Projects/AI-Powered-Legal-Issue-classification/nlp-python/graph.py#652-771) → (repeat for each question) → (if done) → [generate_document](file:///d:/Projects/AI-Powered-Legal-Issue-classification/nlp-python/graph.py#777-803)

State is persisted either in-memory (development) or in a PostgreSQL database (production), so conversations survive page refreshes and can be resumed.

### What Makes It Unique or Better
- **Fully conversational and guided** — no forms to fill
- **Multilingual** — operates natively in 9 Indian languages
- **Voice input** — users can speak their answers
- **Dynamic, case-specific questions** — not generic templates
- **Auto-classifies the legal issue** — user doesn't need to know the legal category
- **Cites applicable Indian laws** automatically in the generated document
- **Bilingual PDF output** — one PDF with both regional language and English versions
- **Free** and runs in a browser with no installation
- **Identifies the correct authority** (police station, consumer forum, bank branch, government department) automatically
- **Safety routing** to emergency services or legal professionals when needed

---

## 5. Features & Functionalities

### Complete List of Features

**1. User Authentication (Register/Login)**
Users register with their mobile phone number, full name, and preferred language. Passwords are hashed using BCrypt. Authentication uses JWT tokens, which are validated on every protected API request. The phone number serves as the unique identifier and is automatically pre-filled in generated documents.

**2. Multi-Language Support (9 Indian Languages)**
The system detects the language of user input and responds in the same language throughout the session. Supported languages: English (en), Tamil (ta), Hindi (hi), Telugu (te), Kannada (kn), Malayalam (ml), Marathi (mr), Bengali (bn), and Gujarati (gu). Questions, acknowledgements, confirmation summaries, and document body text are all generated in the detected language.

**3. AI Legal Issue Classification**
Upon receiving the first message from the user, the LLM classifies the issue into one of 14 predefined categories. Classification rules are explicitly defined in the prompt (e.g., "online fraud = Cyber Crime, not Banking Issue"; "threatening phone calls = Harassment/Threat, not Other Civil Complaint"). The classification is shown to the user exactly once at the start.

**4. Dynamic Conversational Interview (Case Wizard)**
A LangGraph-driven state machine asks 4–7 case-specific questions dynamically generated for the user's exact situation. Each question is tailored (e.g., for a consumer complaint, it asks about the product, seller, defect, purchase date; for a theft, it asks about what was stolen, when, and where). Personal questions (name, address) are always appended at the end, not asked mid-session. An evidence question is always included and is category-specific.

**5. Voice Input with Transcript Confirmation**
Users can record their answer as voice audio. The audio is uploaded to the backend. The speech is transcribed (using browser Web Speech API and/or backend processing). The transcript is shown to the user for confirmation before it is submitted as the answer. The voice endpoint supports multilingual transcripts.

**6. Evidence File Upload**
Users can upload an evidence file (photo, screenshot, PDF) during the session. The filename and document type are injected into the AI context, so it can reference the evidence in the generated document (e.g., "Purchase receipt from XYZ Store dated 1 March 2025, uploaded as evidence").

**7. Confirmation & Edit Loop**
After all facts are collected, the system presents a numbered summary of all collected information, translated into the user's language with labels. The user can confirm with "Yes" or edit by saying "No, change [field]." If they confirm, document generation begins.

**8. Bilingual Legal Document Generation**
The Python NLP service generates two versions of the legal document:
- One in the user's primary language (e.g., Tamil)
- One in English
The document includes: Ref No, Date, From (complainant), To (authority or other party), Subject, Salutation, 3 body paragraphs (facts, harm, demand/request), applicable Indian laws cited with bullet points, evidence/enclosures list, closing, signature block with name/phone/place, and a disclaimer box.

**9. Bilingual PDF Export (Download)**
The Java backend's [BilingualPdfService](file:///d:/Projects/AI-Powered-Legal-Issue-classification/backend-java/src/main/java/com/legal/document/service/BilingualPdfService.java#13-443) converts the text content into a professionally formatted A4 PDF using the OpenPDF library. Regional language characters are rendered using embedded Unicode fonts (Noto Sans Tamil, Noto Sans Devanagari, Noto Sans Telugu, etc.). The PDF contains both language versions side by side in separate sections.

**10. Authority Auto-Identification**
The system dynamically identifies and addresses the document to the correct authority based on the case category and facts provided:
- Criminal cases → The Station House Officer (the user's local police station)
- Consumer complaints → The President, District Consumer Disputes Redressal Commission
- Banking issues → The Branch Manager (of the stated bank branch)
- RTI applications → The Public Information Officer (of the named department)
- Employment disputes → Addressed to the employer's office address
- Legal notices → Addressed directly to the other party (landlord, employer, etc.)

**11. Applicable Laws Auto-Citation**
The system automatically includes relevant Indian legal provisions in each document based on the document type and facts. Examples: Consumer Protection Act 2019 for consumer complaints; IT Act 2000 for cyber fraud; CrPC Section 154 for FIR; IPC sections for specific crimes.

**12. Draft Management (Dashboard)**
Users can view all their past and ongoing cases on the Dashboard. Each case is displayed with its reference number (format: LDA-YYYY-XXXXXX), issue type, sub-category, current status (draft / in_progress / ready / completed), and creation date. Completed cases with generated documents can be viewed. Drafts can be deleted.

**13. Case Resumption**
A previously started case (draft) can be resumed. The conversation history and all collected facts are reloaded from the database, and the session continues from where it left off.

**14. Next Steps Guidance**
After a document is generated, the AI generates 3–5 practical, case-specific next steps for the user — such as where to submit the complaint, which helpline to call, specific government portals to use.

**15. Dark/Light Theme Toggle**
The UI supports a toggleable dark mode/light mode, with the preference stored in localStorage.

**16. Safety Routing**
If a user describes an immediate danger (physical threat to life), the system redirects to emergency numbers (100 Police, 112 Emergency) and declines to generate a document. If the matter requires complex litigation beyond plain document preparation, the user is referred to a qualified legal professional.

---

## 6. System Details

### Frontend
- **Framework:** React.js (v19.2) with Vite (v7.2) as the build tool
- **Routing:** React Router DOM (v6.22)
- **HTTP Client:** Axios (v1.6)
- **Styling:** Vanilla CSS (custom, no framework like Tailwind) — modular per-component CSS files
- **Language:** JavaScript (JSX)
- **Build Tool:** Vite — extremely fast HMR and build times
- **Port:** 5173 (development)

### Backend
- **Framework:** Spring Boot 3.2.1 (Java 17)
- **Security:** Spring Security + JWT (JJWT 0.11.5)
- **ORM:** Spring Data JPA (Hibernate)
- **Database Driver:** PostgreSQL (production), H2 in-memory/file-based (development fallback)
- **PDF Generation:** OpenPDF 1.3.30 (com.github.librepdf)
- **Build Tool:** Apache Maven
- **Utilities:** Lombok (for cleaner Java code), spring-dotenv (for .env file support)
- **Port:** 8080

### AI/NLP Engine
- **Language:** Python 3.8+
- **Framework:** FastAPI (for the HTTP API server), Uvicorn (ASGI server)
- **AI Orchestration:** LangGraph (stateful agent workflow) + LangChain Core
- **LLM Provider:** Groq API — specifically the **llama-3.3-70b-versatile** model
  - Temperature: 0.2 (for consistent, factual outputs)
  - Groq was chosen for its extremely low-latency inference on large models
- **Persistence:** LangGraph checkpoint with PostgreSQL (via psycopg3/psycopg-pool); falls back to in-memory MemorySaver if DB unavailable
- **Key Libraries:**
  - `langgraph` — stateful workflow graph
  - `langchain-groq` — Groq LLM integration
  - `langchain-core` — message types, system/human messages
  - `langchain-community` — additional tools
  - `langgraph-checkpoint-postgres` — persistent conversation state
  - `psycopg-binary`, `psycopg-pool` — PostgreSQL connections
  - `google-generativeai` — (imported, potentially used for fallback)
  - `fastapi`, `uvicorn[standard]`, `pydantic`, `python-multipart`, `httpx`
- **Port:** 8000

### Database
- **Primary (Production):** PostgreSQL 15
- **Development Fallback:** H2 (embedded Java database, file-based mode)
- **Schema Highlights:** 9 tables — users, user_sessions, legal_cases, case_entities, qa_interactions, voice_transcripts, generated_documents, document_versions, document_templates, audit_log
- **Functions/Triggers:** Auto-generated reference numbers (LDA-YYYY-000001 format), auto-update timestamps on record modifications

### APIs & External Services
- **Groq API** — cloud-hosted inference for Llama 3.3 70B Versatile model. API key required.
- **Browser Web Speech API** — for voice input transcription on the frontend (no external API cost)

### Infrastructure & Deployment
- **Docker Compose** — provides containerised deployment for all 4 services: PostgreSQL, Python NLP, Java Backend, React Frontend
- **Nginx** — commented out in docker-compose but prepared for production as a reverse proxy
- **Docker networks** — all services communicate over a private `legal-doc-network` bridge network
- **Health checks** — configured for all services in docker-compose

### Fonts (PDF Rendering)
The Java backend embeds Unicode-aware Noto Sans fonts for all supported scripts:
- NotoSansTamil-Regular.ttf, NotoSansDevanagari-Regular.ttf, NotoSansTelugu-Regular.ttf, NotoSansKannada-Regular.ttf, NotoSansMalayalam-Regular.ttf, NotoSans-Regular.ttf

### Hardware Requirements
No special hardware is required. The system runs on:
- Any standard development machine (Windows/Linux/Mac) with 8GB+ RAM
- For production: a Linux server (cloud VM) with at least 2 CPU cores and 4GB RAM
- Groq API handles all LLM inference in the cloud; no GPU is required locally

---

## 7. Modules Breakdown

### Module 1: Frontend (React.js)
The frontend is a Single Page Application (SPA) with the following route-based pages:

- **Home Page (`/`):** Landing page for the application with branding and entry points to login/register.
- **Auth Module (`/login`, `/register`):** Login and Register pages. Communicates with the Java backend's `/api/auth/login` and `/api/auth/register` endpoints. On success, stores JWT token and user info in React context (AuthContext).
- **Dashboard (`/dashboard`):** Lists all the user's past cases fetched from `/api/cases/my-cases`. Displays case reference number, type, status, and creation date. Allows deletion of cases and navigation to each case.
- **Case View (`/case/:caseId`):** Displays the details of a specific completed case — the extracted entities, document metadata, and download link.
- **Case Wizard (`/new-case`):** The primary interaction module. A full chat-style conversational interface where the user interacts with the AI. Composed of sub-components:
  - **CaseWizard.jsx** — the main container; manages chat state, session ID, polling, document payload handling
  - **VoiceRecorder.jsx** — handles audio recording and transcript confirmation
  - **LiveDocumentPreview.jsx** — shows a live preview of the document as it is being generated
  - **NewCase.jsx** — entry point/wrapper for the wizard
- **QuestionFlow ([QuestionFlow.jsx](file:///d:/Projects/AI-Powered-Legal-Issue-classification/frontend/src/components/QuestionFlow/QuestionFlow.jsx)):** Alternative simpler chat flow component
- **Context Providers:**
  - [AuthContext.jsx](file:///d:/Projects/AI-Powered-Legal-Issue-classification/frontend/src/context/AuthContext.jsx) — manages JWT token, user profile, login/logout state globally
  - [ThemeContext.jsx](file:///d:/Projects/AI-Powered-Legal-Issue-classification/frontend/src/context/ThemeContext.jsx) — manages dark/light mode globally
- **ProtectedRoute.jsx** — wraps protected routes to redirect unauthenticated users to the login page

### Module 2: Java Backend (Spring Boot)

**Controllers** (REST API endpoints):
- [AuthController](file:///d:/Projects/AI-Powered-Legal-Issue-classification/backend-java/src/main/java/com/legal/document/controller/AuthController.java#11-41) — `/api/auth/register`, `/api/auth/login` — user registration and login, returns JWT token
- [SessionController](file:///d:/Projects/AI-Powered-Legal-Issue-classification/backend-java/src/main/java/com/legal/document/controller/SessionController.java#15-93) — `/api/session/start`, `/{sessionId}/answer`, `/{sessionId}/answer-voice`, `/{sessionId}/evidence`, `/{sessionId}` (GET), DELETE — manages the entire conversation session lifecycle
- [CaseController](file:///d:/Projects/AI-Powered-Legal-Issue-classification/backend-java/src/main/java/com/legal/document/controller/CaseController.java#15-90) — `/api/cases/create`, `/api/cases/my-cases`, `/api/cases/{id}`, DELETE — manages case creation, retrieval, and deletion
- [DocumentController](file:///d:/Projects/AI-Powered-Legal-Issue-classification/backend-java/src/main/java/com/legal/document/controller/DocumentController.java#13-74) — `/api/documents/generate-bilingual` — receives the document payload from the frontend and renders the final PDF bytes
- `HealthController` — `/actuator/health` and basic health endpoints for Docker healthchecks

**Services** (Business Logic):
- `AuthService` — handles user creation, BCrypt password hashing, JWT generation
- `SessionService` — manages session state: starts sessions, forwards user messages to the Python NLP service, stores conversation history (CaseAnswer entities), handles voice transcripts, manages draft saving/resumption
- [CaseService](file:///d:/Projects/AI-Powered-Legal-Issue-classification/backend-java/src/main/java/com/legal/document/service/CaseService.java#23-161) — CRUD operations for LegalCase entities and their associated CaseEntity (extracted facts) records
- [LegalServiceAgent](file:///d:/Projects/AI-Powered-Legal-Issue-classification/backend-java/src/main/java/com/legal/document/service/LegalServiceAgent.java#11-53) — the bridge between Java and Python: makes HTTP POST calls to `http://localhost:8000/process` with thread_id and message, returns the AI response as a Map
- [BilingualPdfService](file:///d:/Projects/AI-Powered-Legal-Issue-classification/backend-java/src/main/java/com/legal/document/service/BilingualPdfService.java#13-443) — converts plain text document content into a professionally formatted A4 PDF using OpenPDF, with multi-script Unicode font support

**Entities** (JPA Database Models):
- [User](file:///d:/Projects/AI-Powered-Legal-Issue-classification/backend-java/src/main/java/com/legal/document/service/CaseService.java#85-92) — phone number, email, name, preferred language
- `LegalCase` — reference number, issue type, sub-category, status, suggested authority
- `CaseSession` — maps a conversation thread to a case
- `CaseAnswer` — stores each Q&A pair in the conversation
- `CaseEntity` — stores extracted fact key-value pairs with confidence scores and confirmation flags
- `ExtractedEntity` — additional extracted entity storage
- `GeneratedDocument` — metadata about generated documents (type, language, file format, path)
- `DocumentTemplateEntity` — stores reusable document templates
- `DBFile` — stores uploaded evidence files as binary data
- `DocumentVersion` — JSONB snapshots of document edit history

**Security:**
- `SecurityConfig` — configures Spring Security, CORS, JWT filter chain
- `JwtAuthenticationFilter` — intercepts every request, validates the JWT from the Authorization header
- `JwtUtil` — JWT creation, validation, phone number extraction

**Utilities:**
- `ReferenceNumberGenerator` — generates unique case references in the format `LDA-YYYY-XXXXXX`

### Module 3: Python NLP Engine

**main.py** — FastAPI application entry point. Exposes a single POST endpoint `/process` that accepts `{thread_id: str, message: str}` and returns `{result: dict}`.

**llm_provider.py** — Initialises the Groq LLM client (`langchain-groq`) with the `llama-3.3-70b-versatile` model at temperature 0.2. Loads the GROQ_API_KEY from the [.env](file:///d:/Projects/AI-Powered-Legal-Issue-classification/.env) file.

**graph.py** — The core AI logic. Implements a LangGraph `StateGraph` with 4 nodes:
- [detect_language_node](file:///d:/Projects/AI-Powered-Legal-Issue-classification/nlp-python/graph.py#162-182) — detects the ISO 639-1 language code of the user input
- [classify_and_plan_node](file:///d:/Projects/AI-Powered-Legal-Issue-classification/nlp-python/graph.py#221-646) — the main logic hub: on Turn 1, classifies the issue and builds the interview plan; on subsequent turns, extracts the factual answer to the current question; handles the confirming stage; handles prefill data from the Java backend
- [respond_node](file:///d:/Projects/AI-Powered-Legal-Issue-classification/nlp-python/graph.py#652-771) — generates the response text for the user: classification acknowledgement, next question (translated to user's language), confirmation summary, safety refusal, or professional referral
- [generate_document_node](file:///d:/Projects/AI-Powered-Legal-Issue-classification/nlp-python/graph.py#777-803) — calls `bilingual_generator.generate_bilingual_document()` when user confirms, assembles the full response payload including next steps

State object ([LegalState](file:///d:/Projects/AI-Powered-Legal-Issue-classification/nlp-python/graph.py#39-56)) tracks: messages, thread_id, primary_language, collected_facts (dict), interview_plan (list of question specs), answered_keys (list), current_question_key, stage (collecting/confirming/done), next_step, intent, category, turn_count, generated_content, readiness_score, last_input_hash (for deduplication), classification_shown.

**bilingual_generator.py** — The document assembly engine. Works in 4 steps:
1. [_classify_intent()](file:///d:/Projects/AI-Powered-Legal-Issue-classification/nlp-python/bilingual_generator.py#222-358) — determines the exact document type (police_complaint_fir, cyber_fraud_complaint, consumer_complaint, legal_notice, workplace_complaint, family_petition, banking_complaint, rti_application, property_dispute, insurance_complaint, civil_petition, general_petition), the correct authority name and location, and whether it's a petition to authority or demand letter to another party
2. [_extract_scalars()](file:///d:/Projects/AI-Powered-Legal-Issue-classification/nlp-python/bilingual_generator.py#363-409) — extracts and formats header values (name, address, subject line)
3. [_generate_body()](file:///d:/Projects/AI-Powered-Legal-Issue-classification/nlp-python/bilingual_generator.py#414-531) — generates 3 body paragraphs using the LLM in the user's language, followed by an evidence list
4. [_assemble_petition()](file:///d:/Projects/AI-Powered-Legal-Issue-classification/nlp-python/bilingual_generator.py#649-748) / [_assemble_demand_letter()](file:///d:/Projects/AI-Powered-Legal-Issue-classification/nlp-python/bilingual_generator.py#753-852) — constructs the full plain-text document: date header, From block, To block, Subject, salutation, body, applicable laws, enclosures, closing, signature block, disclaimer

Also includes [get_applicable_laws()](file:///d:/Projects/AI-Powered-Legal-Issue-classification/nlp-python/bilingual_generator.py#536-618) which maps document type + facts keywords to specific Indian legal provisions.

### Module 4: Database

The PostgreSQL schema has 9 interconnected tables with cascade-delete constraints, performance indexes, and triggers for automatic timestamp management. A stored function `generate_reference_number()` creates unique case reference numbers. Sample data seeds initial document templates.

---

## 8. System Architecture

### End-to-End Data Flow

**Step 1 — User Registration/Login**
The user opens the React frontend at `http://localhost:5173`. They register with phone number, full name, password, and preferred language. The frontend sends a POST to `http://localhost:8080/api/auth/register`. Spring Boot hashes the password with BCrypt, saves the user to PostgreSQL, generates a JWT token, and returns it. The token is stored in React's AuthContext and sent in the `Authorization: Bearer <token>` header on all subsequent requests.

**Step 2 — Starting a New Case**
The user clicks "New Case" and is taken to the CaseWizard. The wizard starts a session by sending a POST to `/api/session/start` with the user's initial problem description message. The Java backend extracts the user's phone number from the JWT, looks up the user profile (including their phone number — which will be prefilled in the document), creates a new `CaseSession` record in the database with a unique UUID as the thread_id, constructs a prefill message (e.g., `__PREFILL__ user_phone="9876543210" user_full_name="Karthik" || <actual user message>`), and forwards this composite message to the Python NLP service at `http://localhost:8000/process`.

**Step 3 — AI Processing (Turn 1)**
The Python NLP engine receives the request. LangGraph invokes:
1. [detect_language_node](file:///d:/Projects/AI-Powered-Legal-Issue-classification/nlp-python/graph.py#162-182) → sets `primary_language = "ta"` (or whatever is detected)
2. [classify_and_plan_node](file:///d:/Projects/AI-Powered-Legal-Issue-classification/nlp-python/graph.py#221-646) → calls Groq Llama 70B with a detailed classification prompt → receives `{category, policy_action, initial_facts, interview_plan}` → appends authority-specific questions and personal questions to the plan → strips personal keys already prefilled
3. [respond_node](file:///d:/Projects/AI-Powered-Legal-Issue-classification/nlp-python/graph.py#652-771) → formats the first question in the user's language — showing the classification context line first, then the first interview question text

The response `{content, entities, intent, readiness_score, is_document, is_confirmation, next_steps}` is returned to the Java backend.

**Step 4 — Response Relay and Storage**
Java `SessionService` receives the response dict, stores the Q&A pair in the `case_answer` table, and sends the response JSON back to the React frontend. The frontend displays the AI message as a chat bubble in the CaseWizard.

**Step 5 — Subsequent Turns (Answer Extraction Loop)**
The user types or speaks their answer. The frontend sends it to `/api/session/{sessionId}/answer`. Java relays it to Python with the same thread_id. LangGraph loads the saved state from the PostgreSQL checkpoint, runs [classify_and_plan_node](file:///d:/Projects/AI-Powered-Legal-Issue-classification/nlp-python/graph.py#221-646) in extract mode (LLM extracts the factual answer for the current question key), updates `collected_facts`, advances the interview plan, and runs [respond_node](file:///d:/Projects/AI-Powered-Legal-Issue-classification/nlp-python/graph.py#652-771) to generate the next question. This repeats until all questions are answered.

**Step 6 — Confirmation Stage**
When all questions are answered, [respond_node](file:///d:/Projects/AI-Powered-Legal-Issue-classification/nlp-python/graph.py#652-771) generates a numbered confirmation summary in the user's language. The frontend renders this in a distinct "confirmation" style (highlighted box). The user types "Yes" or "Correct". LangGraph handles confirmation by transitioning `stage = done` and routing to [generate_document](file:///d:/Projects/AI-Powered-Legal-Issue-classification/nlp-python/graph.py#777-803).

**Step 7 — Document Generation**
[generate_document_node](file:///d:/Projects/AI-Powered-Legal-Issue-classification/nlp-python/graph.py#777-803) calls `bilingual_generator.generate_bilingual_document(intent, facts, lang)`. This calls Groq 3 more times: (a) to classify the document type and identify the authority, (b) to write the subject line, (c) to generate the 3-paragraph body + evidence list in the user's language. It also generates a parallel English version. The result is two plain-text document strings plus metadata. This is serialised as JSON and returned as `DOCUMENT_READY\n{...json...}`.

**Step 8 — PDF Rendering**
The frontend receives the `is_document: true` response, parses the JSON payload, and offers the user a "Download PDF" button. When clicked, it sends a POST to the Java backend `/api/documents/generate-bilingual` with the two document content strings and metadata. The Java [BilingualPdfService](file:///d:/Projects/AI-Powered-Legal-Issue-classification/backend-java/src/main/java/com/legal/document/service/BilingualPdfService.java#13-443) renders the content into an A4 PDF with proper Unicode fonts, bilingual layout, and a disclaimer box, returning the PDF bytes. The browser triggers the file download as `SattaVizhi_<document_type>.pdf`.

### Additional Flows
- **Voice Input:** User records audio → frontend uploads to `/api/session/{sessionId}/answer-voice` → Java saves audio file to DB, extracts transcript → forwards transcript to Python NLP → same processing as text answer
- **Evidence Upload:** User uploads file → stored as binary in `db_file` table → filename injected into Python as `I have uploaded evidence: <filename>` → AI notes it in `evidence_available` fact
- **Draft Resumption:** User clicks existing draft on Dashboard → frontend navigates to `/new-case?caseId=<id>` → retrieves session history → Python loads state from PostgreSQL checkpoint for that thread_id → conversation continues

---

## 9. Users & Impact

### Who Will Use This System
**Primary users:**
- Citizens of India who are victims of crime, consumer fraud, workplace exploitation, cyber crime, property disputes, banking irregularities, or insurance claim rejection
- First-generation smartphone users in semi-urban and rural India
- Migrant workers who face salary theft or exploitative landlords
- Senior citizens who struggle to interact with digital government systems

**Secondary users:**
- Lawyers and legal aid workers who want to quickly generate accurate first-draft documents for their clients
- NGOs providing legal aid to marginalised communities
- College students studying law who want to understand document drafting

### How It Benefits Users
- **Time savings:** A document that would take a lawyer 1–2 hours to draft (including the client interview) is generated in under 15 minutes
- **Cost savings:** Zero cost vs. Rs. 500–5000 that legal drafting typically costs
- **Language accessibility:** Users who cannot read or write English can still generate an English legal document
- **Empowerment:** Users who were previously unaware of their rights learn which authority to approach and what legal provisions protect them
- **Accuracy:** The document contains specific dates, amounts, names, and legal sections — far more accurate than a hand-written complaint

### Real-World Applications
- A domestic worker whose salary was withheld can generate a workplace complaint to the Labour Commissioner in Tamil
- A farmer whose crop was stolen can file a police FIR complaint drafted in Hindi
- A consumer who received a defective TV can file a consumer forum petition with applicable Consumer Protection Act sections
- A tenant whose security deposit was not returned can generate a legal notice to the landlord
- A bank account holder who suffered unauthorised debits can file a banking complaint to the RBI Banking Ombudsman
- A citizen seeking information under RTI can generate a proper RTI application to the relevant public information officer

---

## 10. Ethical & Safety Aspects

### Data Privacy Considerations
- **Phone number as primary identifier:** User phone numbers are stored in plain text (needed for identification) but passwords are BCrypt-hashed. The system does not store Aadhaar numbers, voter IDs, or other sensitive government identifiers.
- **Voice audio storage:** Voice recordings uploaded during the session are stored as binary data in the database. Users are not explicitly informed of retention policies; this needs a proper privacy policy.
- **LLM data transmission:** All user messages including sensitive personal details (name, address, income, legal grievances) are transmitted to the Groq API for LLM inference. Groq's data handling policies apply. For production deployment, a self-hosted LLM (e.g., Ollama) would be preferable for sensitive legal data.
- **JWT tokens:** Tokens are not explicitly expired at logout beyond client-side deletion. Server-side token blacklisting is not implemented, which is a minor security gap.
- **Evidence files:** Uploaded evidence files (photos, screenshots) are stored directly in the database. For production, these should be encrypted at rest and stored in a secure object store (AWS S3, etc.) with access controls.

### Bias and Fairness Concerns
- **LLM classification bias:** The LLM classifies legal issues based on training data which may reflect societal biases. For example, issues involving women, minorities, or Dalits may be classified differently than the same factual situation involving a majority-group complainant. This is a known limitation of LLM-based classification.
- **Language quality bias:** The quality of classification and document generation may be higher for English and Hindi (better-trained languages in Llama 70B) than for less-resource languages like Gujarati or Bengali.
- **Legal system bias:** The system assumes the Indian legal framework applies. Citizens from other countries or in diaspora situations are explicitly directed to seek professional help instead (the `refer_professional` safety action).
- **Category limitations:** The 14 legal categories cover most common civil and criminal grievances but may not cover niche areas (e.g., intellectual property, environmental law, immigration law).

### Legal and Ethical Risks
- **Not legal advice:** The system explicitly disclaims this on every generated document: "This document has been automatically generated based solely on information provided by the user. It does not constitute legal advice." This disclaimer is included in both languages.
- **Accuracy risk:** If a user provides false or incorrect information, the document will faithfully reflect that incorrect information. The system does not verify facts.
- **Misuse potential:** Someone could use the system to generate fraudulent legal documents (e.g., filing a false FIR). The safety routing attempts to block clearly unethical requests but is not foolproof.
- **No legal warranties:** The system cannot guarantee that a generated document meets the formal requirements of every Indian state, court, or authority. Formats may vary by jurisdiction.

---

## 11. Sustainability / Broader Impact

### Societal and Global Goals
This project directly supports several United Nations Sustainable Development Goals (SDGs):
- **SDG 16 — Peace, Justice and Strong Institutions:** "Provide access to justice for all and build effective, accountable institutions." Satta Vizhi directly democratises access to justice by removing financial and linguistic barriers.
- **SDG 10 — Reduced Inequalities:** Specifically targets the gap in legal access between wealthy, English-literate urban citizens and rural, regional-language-speaking communities.
- **SDG 4 — Quality Education:** Indirectly supports legal literacy by showing users which laws apply to their situation.

Within India, the project aligns with:
- **Digital India initiative** — making digital government services accessible to all citizens
- **Legal Aid Services Authority mandates** — extending free legal assistance to economically weaker sections
- **BharatNet / PM-WANI** — as rural internet connectivity improves, the web-based system becomes available to more people

### Long-Term Impact
If deployed at scale, Satta Vizhi could:
- Significantly increase the reporting rate of petty crimes (theft, harassment) that go unreported due to the burden of filing
- Reduce exploitation of workers, tenants, and consumers who previously had no affordable recourse
- Create a large dataset of anonymised legal complaints that can be used for legal research and judiciary analytics
- Serve as a model that other developing nations with multilingual legal systems could replicate

---

## 12. Development & Management

### Development Methodology
The project follows an **iterative, feature-driven development** approach similar to Agile/Scrum sprint cycles, though without a formal Scrum framework. Development progressed in short cycles with regular testing and feedback loops, each adding functionality to the existing core.

### Key Development Phases (Chronological)
Based on conversation history and code analysis:

1. **Phase 1 (Initial Setup — February 2026):** Full-stack project setup — Spring Boot backend, React frontend, PostgreSQL schema design, basic JWT authentication, initial project structure
2. **Phase 2 (Core NLP Engine):** LangGraph graph implementation, LLM integration (Groq API), basic classification and question generation, document generation pipeline
3. **Phase 3 (Data Refinement):** Fixing draft resumption/continuation, relative date input handling ("today", "yesterday"), deletion bug fixes
4. **Phase 4 (Document Quality):** Refining document generation quality — improving bilingual output, fixing language quality, PDF formatting with Unicode fonts, download functionality
5. **Phase 5 (Voice & Evidence):** Voice input transcription, evidence file upload, voice answer processing pipeline
6. **Phase 6 (Debugging & Stabilisation — March 2026):** NLP service debugging, improving LLM response parsing, edge case handling, error recovery, service health checking

### Team Roles
The project appears to have been primarily developed by a single developer (the user), assisted by an AI pair-programmer for code generation, debugging, and architectural decisions.

---

## 13. Cost & Resources

### Development Costs
- **Developer time:** Primary cost is developer hours (if commercialised). Estimated 3–6 months of part-time or full-time development.
- **Groq API:** Groq offers a free tier and very low-cost paid usage. Llama 3.3 70B Versatile is approximately $0.59 per 1 million input tokens and $0.79 per 1 million output tokens. For a single session of ~15 turns, estimated API cost per completed case is approximately $0.002–0.005 (fractions of a cent).
- **Google Generative AI (google-generativeai):** Imported in requirements.txt — potentially used as a fallback or for specific tasks. If using Gemini, similar pricing applies.
- **Development tools:** All free/open source — VS Code, Java JDK, Maven, Python, Node.js, PostgreSQL, Docker.

### Resources Required for Deployment
- **Cloud VM:** A standard Linux VPS with 2 vCPU / 4GB RAM is sufficient for running all 4 Docker containers. Estimated cost: $15–40/month (e.g., AWS EC2 t3.medium, DigitalOcean Droplet).
- **Object Storage (for production evidence files):** AWS S3 or similar — minimal cost for small-scale deployment.
- **Domain + SSL:** ~$10–15/year for domain + free SSL via Let's Encrypt.
- **No GPU required** — all LLM inference is done via API.

Total estimated monthly operational cost for a small-scale deployment servicing a few hundred users: **approximately $15–50/month**.

---

## 14. Results & Future Scope

### What Has Been Achieved So Far
- A complete, working three-service system: Python AI engine, Java REST backend, React frontend — all integrated and functional
- Multi-language support for 9 Indian languages in both Q&A (conversational) and document generation modes
- 14 legal category classifications with accurate routing
- Dynamic, case-specific interview generation powered by Llama 3.3 70B
- Bilingual PDF generation with Unicode fonts for Tamil, Hindi, Telugu, Kannada, Malayalam scripts
- Applicable Indian law auto-citation in documents
- Voice input with transcript confirmation
- Evidence file upload with document context injection
- Draft saving, resumption, and deletion
- JWT-based authentication with BCrypt password hashing
- Docker Compose deployment configuration
- PostgreSQL persistent state for conversation history (LangGraph checkpointing)
- Auto-population of user details (phone number) from auth token into document
- Safety routing (emergency services, professional referral)

### Possible Improvements and Future Enhancements

**Near-term:**
1. **Self-hosted LLM option:** Integrate Ollama to allow running Llama locally for full data privacy — important for sensitive legal use
2. **Android/iOS mobile app:** A native app with better voice support and offline capability
3. **Actual OCR for evidence:** Automatically extract text from uploaded receipts or screenshots using OCR (Tesseract or Google Cloud Vision) to pre-fill certain facts
4. **SMS/WhatsApp integration:** Allow users to interact via WhatsApp Business API for users without smartphone browsers
5. **Enhanced voice support:** Implement Whisper (OpenAI) or Google Speech-to-Text for more accurate multilingual transcription, especially for regional languages

**Medium-term:**
6. **Expanded category support:** Motor accident compensation, domestic violence protection orders, environmental complaints, immigration assistance
7. **Legal professional portal:** A secondary interface where lawyers and NGOs can manage clients and review AI-generated documents before submission
8. **Digital signature integration:** Allow users to digitally sign the generated document via Aadhaar-based eSign (DigiLocker)
9. **Direct e-filing integration:** API connectors to Tamil Nadu e-districts portal, NCRB cybercrime portal, Maharashtra RTI portal for direct digital submission
10. **Analytics dashboard:** Aggregate (anonymised) statistics on complaint types by region — useful for legal researchers and NGOs

**Long-term:**
11. **Case outcome tracking:** Allow users to record the outcome of their complaint (FIR registered, complaint resolved, court decision) — creating a feedback loop that could be used to assess legal system effectiveness
12. **AI legal advisor mode:** Beyond document drafting, provide conditional legal information ("In your situation, under Section 379 IPC, the accused could face up to 3 years of imprisonment...") — clearly labelled as information, not advice
13. **Multi-state legal variation handling:** Indian states have different local laws and procedures (e.g., Tamil Nadu's Patta system for land records). State-specific templates and procedures would improve accuracy.
14. **Open API for NGOs:** Provide a documented REST API so that legal aid NGOs can integrate Satta Vizhi into their own systems.

---

## 15. References / Sources

### AI/LLM
- **Groq API Documentation:** https://console.groq.com/docs — Groq's cloud LLM inference platform, used for ultra-low-latency inference of Meta's Llama 3.3 70B Versatile model
- **Meta Llama 3.3:** https://ai.meta.com/blog/llama-3/ — the underlying LLM model
- **LangChain Documentation:** https://python.langchain.com/docs — LangChain framework used for LLM message formatting and integrations
- **LangGraph Documentation:** https://langchain-ai.github.io/langgraph/ — stateful agent workflow graph orchestration

### Backend / Java
- **Spring Boot 3.2 Documentation:** https://spring.io/projects/spring-boot
- **Spring Security Documentation:** https://docs.spring.io/spring-security/
- **JJWT (Java JWT) Library:** https://github.com/jwtk/jjwt
- **OpenPDF Library:** https://github.com/LibrePDF/OpenPDF — open-source PDF generation in Java
- **Noto Sans Fonts (Google):** https://fonts.google.com/noto — Unicode-compliant fonts for Indian scripts

### Frontend
- **React.js Documentation:** https://react.dev/
- **Vite Documentation:** https://vitejs.dev/
- **React Router DOM:** https://reactrouter.com/

### Database
- **PostgreSQL 15 Documentation:** https://www.postgresql.org/docs/15/
- **H2 Database (Java):** https://www.h2database.com/

### Legal References (Indian Law — used in the system's legal citation logic)
- **Indian Penal Code (IPC) 1860** — Sections 323, 354, 379, 380, 420, 506, 509
- **Code of Criminal Procedure (CrPC) 1973** — Section 154 (FIR), Section 125 (Maintenance)
- **Information Technology Act 2000** — Sections 66C, 66D
- **Consumer Protection Act 2019** — Sections 2(7), 2(10), 2(47), 35
- **Right to Information Act 2005** — Sections 6, 7
- **Industrial Disputes Act 1947** — Sections 2(s), 25F
- **Payment of Wages Act 1936** — Section 5
- **Sexual Harassment of Women at Workplace Act 2013**
- **Banking Regulation Act 1949**
- **Reserve Bank of India Act 1934**
- **Payment and Settlement Systems Act 2007**
- **Insurance Act 1938**
- **IRDAI (Protection of Policyholders' Interests) Regulations 2017**
- **Transfer of Property Act 1882**
- **Indian Contract Act 1872** — Section 73
- **Specific Relief Act 1963** — Sections 9, 38
- **Indian Easements Act 1882**
- **Hindu Marriage Act 1955** — Sections 13, 24
- **Civil Procedure Code 1908** — Order 37

### Development Environment
- **Docker / Docker Compose:** https://docs.docker.com/ — containerisation for deployment
- **Apache Maven:** https://maven.apache.org/ — Java build tool
- **Python FastAPI:** https://fastapi.tiangolo.com/ — Python async REST API server
- **Uvicorn:** https://www.uvicorn.org/ — ASGI server for FastAPI

---

*Report generated: 24 March 2026 | Project: Satta Vizhi | Status: Functional prototype, under active development*
