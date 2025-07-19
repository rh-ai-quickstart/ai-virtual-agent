# Document Ingestion Directory

This directory contains documents that can be ingested into the AI Virtual Agent platform to create knowledge bases for specialized agents.

## 📚 Available Document Collections

### Banking & Financial Services

#### Compliance & Regulations
- **Path**: `data/compliance/compliance.md`
- **Size**: 4.8KB, 149 lines
- **Content**: U.S. banking compliance regulations including BSA/AML, OFAC, CFPB, Dodd-Frank, and regulatory bodies
- **Use Case**: Compliance officers, regulatory specialists, risk management

#### Loan Processing & Underwriting
- **Path**: `data/banking/loan-processing.md`
- **Size**: 7.3KB, 303 lines
- **Content**: SBA loan programs, commercial loan underwriting, financial ratios, credit assessment
- **Use Case**: Loan officers, credit analysts, business bankers

#### Fraud Detection & AML Procedures
- **Path**: `data/banking/fraud-detection.md`
- **Size**: 9.4KB, 331 lines
- **Content**: Money laundering red flags, OFAC screening, CTR/SAR procedures, investigation protocols
- **Use Case**: AML investigators, fraud analysts, compliance officers

#### Customer Service & Account Operations
- **Path**: `data/banking/customer-service.md`
- **Size**: 9.9KB, 371 lines
- **Content**: Account opening procedures, transaction limits, identity verification, customer dispute resolution
- **Use Case**: Customer service representatives, tellers, branch operations

#### Business Banking Procedures
- **Path**: `data/banking/business-banking.md`
- **Size**: 11KB, 362 lines
- **Content**: Business account opening, commercial transactions, business verification, risk management
- **Use Case**: Business bankers, relationship managers, commercial lenders

## 🚀 How to Ingest via UI

### Using Git Repository as Source

1. **Access the UI**: Navigate to Knowledge Bases section in the AI Virtual Agent frontend
2. **Create Knowledge Base**: Click "Create Knowledge Base"
3. **Configure Source**: Select "GitHub" as the source
4. **Repository Settings**:
   - **Repository URL**: Your repository URL
   - **Path**: Choose the specific directory (e.g., `ingest/data/compliance/`)
   - **Branch**: `main` (or your current branch)
5. **Create**: Click "Create" to start ingestion

### Recommended Knowledge Base Names

| Document | Knowledge Base Name | Vector DB Name |
|----------|-------------------|----------------|
| `compliance.md` | Banking Compliance & Regulations | `banking-compliance-v1` |
| `loan-processing.md` | Loan Processing & Underwriting | `loan-processing-v1` |
| `fraud-detection.md` | Fraud Detection & AML Procedures | `fraud-detection-v1` |
| `customer-service.md` | Customer Service & Account Operations | `customer-service-v1` |
| `business-banking.md` | Business Banking Procedures | `business-banking-v1` |

## 🎯 FSI Banking Demo Setup

For the FSI Banking Demo, create these 5 knowledge bases:

### Step 1: Banking Compliance
- **Path**: `ingest/data/compliance/`
- **Purpose**: Provides regulatory context for all agents

### Step 2: Loan Processing
- **Path**: `ingest/data/banking/`
- **Purpose**: Enables loan officers to provide accurate guidance

### Step 3: Fraud Detection
- **Path**: `ingest/data/banking/`
- **Purpose**: Enables fraud analysts to identify and investigate risks

### Step 4: Customer Service
- **Path**: `ingest/data/banking/`
- **Purpose**: Enables customer service to handle account inquiries

### Step 5: Business Banking
- **Path**: `ingest/data/banking/`
- **Purpose**: Enables comprehensive business banking support

## 📋 Ingestion Checklist

- [ ] All 5 knowledge bases created via UI
- [ ] All knowledge bases show READY status
- [ ] Knowledge bases properly linked to agents
- [ ] Agents tested with sample questions

## 🔧 Troubleshooting

### Common Issues
- **Path not found**: Ensure the directory path exists in your repository
- **Ingestion stuck**: Check backend logs for errors
- **Access denied**: Verify repository is public or credentials are configured

### Expected Timeline
- **Small documents** (compliance): 2-5 minutes
- **Medium documents** (banking procedures): 5-10 minutes
- **Total time**: 15-30 minutes for all 5 knowledge bases

## 📖 Document Structure

All documents follow a consistent structure optimized for RAG (Retrieval-Augmented Generation):

- **Clear headers** with descriptive titles
- **Structured sections** with bullet points and lists
- **Industry-specific terminology** and acronyms
- **Practical procedures** and step-by-step instructions
- **Regulatory references** and compliance requirements

This structure ensures that AI agents can effectively retrieve and use the information to provide accurate, contextually relevant responses. 