# Document Ingestion Directory

This directory contains documents that can be ingested into the AI Virtual Agent platform to create knowledge bases for specialized agents.

## 📚 Available Document Collections

### Banking & Financial Services

#### Banking Compliance & Regulations
- **Path**: `data/banking-compliance/compliance.md`
- **Size**: 4.8KB, 149 lines
- **Content**: U.S. banking compliance regulations including BSA/AML, OFAC, CFPB, Dodd-Frank, and regulatory bodies
- **Use Case**: Compliance officers, regulatory specialists, risk management

#### Loan Processing & Underwriting
- **Path**: `data/loan-processing/loan-processing.md`
- **Size**: 7.3KB, 303 lines
- **Content**: SBA loan programs, commercial loan underwriting, financial ratios, credit assessment
- **Use Case**: Loan officers, credit analysts, business bankers

#### Fraud Detection & AML Procedures
- **Path**: `data/fraud-detection/fraud-detection.md`
- **Size**: 9.4KB, 331 lines
- **Content**: Money laundering red flags, OFAC screening, CTR/SAR procedures, investigation protocols
- **Use Case**: AML investigators, fraud analysts, compliance officers

#### Customer Service & Account Operations
- **Path**: `data/customer-service/customer-service.md`
- **Size**: 9.9KB, 371 lines
- **Content**: Account opening procedures, transaction limits, identity verification, customer dispute resolution
- **Use Case**: Customer service representatives, tellers, branch operations

#### Business Banking Procedures
- **Path**: `data/business-banking/business-banking.md`
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
   - **Path**: Choose the specific directory (e.g., `ingest/data/banking-compliance/`)
   - **Branch**: `aaas` (or your current branch)
5. **Create**: Click "Create" to start ingestion

### Recommended Knowledge Base Names

| Document | Knowledge Base Name | Vector DB Name | Path |
|----------|-------------------|----------------|------|
| `compliance.md` | Banking Compliance & Regulations | `banking-compliance-v1` | `ingest/data/banking-compliance/` |
| `loan-processing.md` | Loan Processing & Underwriting | `loan-processing-v1` | `ingest/data/loan-processing/` |
| `fraud-detection.md` | Fraud Detection & AML Procedures | `fraud-detection-v1` | `ingest/data/fraud-detection/` |
| `customer-service.md` | Customer Service & Account Operations | `customer-service-v1` | `ingest/data/customer-service/` |
| `business-banking.md` | Business Banking Procedures | `business-banking-v1` | `ingest/data/business-banking/` |

## 🎯 FSI Banking Demo Setup

For the FSI Banking Demo, create these 5 knowledge bases:

### Step 1: Banking Compliance
- **Path**: `ingest/data/banking-compliance/`
- **Purpose**: Provides regulatory context for all agents

### Step 2: Loan Processing
- **Path**: `ingest/data/loan-processing/`
- **Purpose**: Enables loan officers to provide accurate guidance

### Step 3: Fraud Detection
- **Path**: `ingest/data/fraud-detection/`
- **Purpose**: Enables fraud analysts to identify and investigate risks

### Step 4: Customer Service
- **Path**: `ingest/data/customer-service/`
- **Purpose**: Enables customer service to handle account inquiries

### Step 5: Business Banking
- **Path**: `ingest/data/business-banking/`
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
- **Duplicate content**: Each knowledge base now has its own directory to prevent overlap

### Directory Structure
```
ingest/data/
├── banking-compliance/
│   └── compliance.md
├── loan-processing/
│   └── loan-processing.md
├── fraud-detection/
│   └── fraud-detection.md
├── customer-service/
│   └── customer-service.md
└── business-banking/
    └── business-banking.md
```

## 📝 Notes

- **Isolated Content**: Each knowledge base directory contains only the relevant documents
- **No Overlap**: Documents are separated to ensure agents get specific, focused information
- **Scalable**: Easy to add new knowledge bases by creating new directories 