# HR Application - Candidate Ranking System

A Flask-based HR application that helps rank candidates against job descriptions using AI-powered analysis.

## Features

- **Candidate Management**: Upload and manage candidate CVs (PDF, DOCX formats)
- **Job Management**: Create and manage job descriptions
- **AI-Powered Ranking**: Automatically rank candidates against job requirements using LLM and vector embeddings
- **Interactive UI**: User-friendly web interface for all operations

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: SQLite with SQLAlchemy ORM
- **AI/ML**: 
  - LLM integration for intelligent analysis
  - ChromaDB for vector storage and similarity search
- **Frontend**: HTML, CSS, JavaScript

## Project Structure

```
hrapplication/
├── app.py                 # Main application entry point
├── config.py             # Configuration settings
├── extensions.py         # Flask extensions initialization
├── requirements.txt      # Python dependencies
├── models/              # Database models
│   ├── candidate.py
│   ├── job.py
│   └── ranking.py
├── routes/              # Application routes
│   ├── candidate_routes.py
│   ├── job_routes.py
│   └── ranking_routes.py
├── services/            # Business logic
│   ├── cv_parser.py
│   ├── llm_service.py
│   ├── ranking_engine.py
│   └── vector_service.py
├── templates/           # HTML templates
└── static/             # CSS and JavaScript files
```

## Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/sudeshcool/hr.git
   cd hr
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the application**
   Open your browser and navigate to `http://localhost:8080`

## Deployment to Azure

This application can be easily deployed to Azure App Service. See the comprehensive [Azure Deployment Guide](AZURE_DEPLOYMENT.md) for detailed instructions.

### Quick Deploy

```bash
# Make the deployment script executable
chmod +x deploy_to_azure.sh

# Run the deployment script
./deploy_to_azure.sh
```

The script will guide you through the deployment process and automatically:
- Create Azure resources (Resource Group, App Service Plan, Web App)
- Configure application settings
- Deploy your code to Azure
- Enable HTTPS

For manual deployment or CI/CD setup, refer to [AZURE_DEPLOYMENT.md](AZURE_DEPLOYMENT.md).

## Environment Variables

Create a `.env` file based on `.env.example`:

- `SECRET_KEY`: Flask secret key for session management
- `DATABASE_URL`: Database connection string (default: SQLite)
- `LLM_API_KEY`: API key for LLM service
- Other configuration as needed

## Usage

1. **Add Job Descriptions**: Create job postings with detailed requirements
2. **Upload Candidate CVs**: Upload resumes in PDF or DOCX format
3. **Run Ranking**: Match candidates against job descriptions
4. **Review Results**: View ranked candidates with detailed analysis

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.