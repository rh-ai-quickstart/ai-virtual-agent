# FSI Banking Demo - Execution Checklist

## 🎯 Quick Start (5 minutes)

**Assumption**: You have access to the UI with templates and knowledge bases already created.

---

##  Pre-Demo Checklist

### **Knowledge Bases Status**
- [ ] **5 knowledge bases created** and show "READY" status:
  - Banking Compliance & Regulations (`banking-compliance-v1`) - Path: `ingest/data/banking-compliance/`
  - Loan Processing & Underwriting (`loan-processing-v1`) - Path: `ingest/data/loan-processing/`
  - Fraud Detection & AML Procedures (`fraud-detection-v1`) - Path: `ingest/data/fraud-detection/`
  - Customer Service & Account Operations (`customer-service-v1`) - Path: `ingest/data/customer-service/`
  - Business Banking Procedures (`business-banking-v1`) - Path: `ingest/data/business-banking/`

### **MCP Server Status**
- [ ] **MCP Server configured** and shows "READY" status:
  - Go to **Config** → **MCP Servers**
  - Verify `mcp::dbstore` server is listed with endpoint: `http://mcp-dbstore-standalone:8002/sse`
  - Status should show as active/connected

### **Template Status**
- [ ] **FSI Banking template** is available in the UI
- [ ] Template shows **6 agents** across **5 personas**
- [ ] Agents are configured with both **RAG tools** (knowledge bases) and **MCP tools** (database access)

---

## 🚀 Demo Execution Steps

### **Step 1: Verify MCP Server Integration (1 minute)**

#### **Test MCP Server Connection**
1. Go to **Config** → **MCP Servers**
2. Verify `mcp::dbstore` server is listed and active
3. Note the endpoint: `http://mcp-dbstore-standalone:8002/sse`

#### **Test Database Access**
1. Go to **Chat** section
2. Create a **test agent** with MCP tools:
   - Name: `Database Test Agent`
   - Model: `meta-llama/Llama-3.1-8B-Instruct`
   - Tools: Select `mcp::dbstore`
   - Knowledge Bases: Leave empty (testing MCP only)
3. Ask: *"What tables are available in the database?"*
4. Verify response includes database schema information

### **Step 2: Deploy Demo Agents (2 minutes)**

#### **Deploy Customer Service Representative**
1. Go to **Templates** → **FSI Banking** → **Branch Operations**
2. Click **"Customer Service Representative"**
3. Click **"Deploy Agent"**
4. Note the **Agent ID** for later use

#### **Deploy AML Investigator**
1. Go to **Templates** → **FSI Banking** → **Fraud Analyst**
2. Click **"AML Investigator"**
3. Click **"Deploy Agent"**
4. Note the **Agent ID** for later use

#### **Deploy Commercial Loan Officer**
1. Go to **Templates** → **FSI Banking** → **Relationship Manager**
2. Click **"Commercial Loan Officer"**
3. Click **"Deploy Agent"**
4. Note the **Agent ID** for later use

### **Step 3: Test Each Agent (3 minutes)**

#### **Test Customer Service Agent**
1. Go to **Chat** section
2. Select the **Customer Service Representative** agent
3. Ask: *"Hi, I'm a customer service rep at Horizon Community Bank. A business owner just came in with a loan application for $250,000. The business is called 'Tech Solutions LLC' and they want to expand their operations. What should I do first?"*
4. Verify response includes: documentation requirements, procedures, timeline
5. **Bonus MCP Test**: Ask *"Can you search the database for any existing records for Tech Solutions LLC?"*

#### **Test AML Investigator**
1. Switch to **AML Investigator** agent
2. Ask: *"I'm reviewing the Tech Solutions LLC loan application. The business was incorporated only 3 months ago, but they're requesting $250,000. The owner has no prior banking history with us, and the business address is a residential property. What red flags should I investigate?"*
3. Verify response includes: specific red flags, investigation steps, compliance requirements
4. **Bonus MCP Test**: Ask *"Search the database for any records related to Red Flag Business or similar high-risk applications."*

#### **Test Commercial Loan Officer**
1. Switch to **Commercial Loan Officer** agent
2. Ask: *"I'm the commercial loan officer reviewing the Tech Solutions LLC application. The fraud team has flagged some concerns, but the business plan looks solid. They have a $50,000 deposit and good credit score. What factors should I consider for approval, and what additional documentation should I request?"*
3. Verify response includes: credit assessment factors, risk mitigation, additional documentation
4. **Bonus MCP Test**: Ask *"Search the database for similar loan applications and show me the approval patterns."*

---

## 🎬 Multi-Person Demo Script (8-10 minutes)

### **Demo Team Roles**

#### **👤 Presenter 1: Sarah Chen - Banking Operations Manager**
- **Role**: Demonstrates customer service workflow and initial loan processing
- **Expertise**: Branch operations, customer experience, regulatory procedures
- **Focus**: Professional customer interaction and process efficiency

#### **👤 Presenter 2: Marcus Rodriguez - Compliance & Risk Officer**
- **Role**: Handles fraud detection and compliance investigation
- **Expertise**: AML procedures, regulatory compliance, risk assessment
- **Focus**: Risk management and regulatory adherence

#### **👤 Presenter 3: Jennifer Park - Senior Commercial Lender**
- **Role**: Makes final credit decision and loan structuring
- **Expertise**: Commercial lending, credit analysis, business development
- **Focus**: Credit decision-making and business growth

### **Opening (1 minute) - Sarah Chen**
*"Welcome everyone! I'm Sarah Chen, Banking Operations Manager at Horizon Community Bank. Today we'll demonstrate how our AI Virtual Agent platform transforms complex banking workflows. We'll follow a real business loan application through three critical stages, showing how different AI agents work together to ensure compliance, manage risk, and deliver excellent customer service. Our agents can access both our knowledge base and live database systems for comprehensive decision-making."*

### **Demo Scenario: Tech Solutions LLC - $250,000 Business Loan Application**

#### **🎯 Stage 1: Customer Service & Initial Processing (2-3 minutes) - Sarah Chen**

**Sarah's Introduction:**
*"Let me start by showing you how our Customer Service Representative agent handles the initial loan application. This agent has access to our procedures database and can also query our live customer database for real-time information."*

**Action**: Sarah switches to Customer Service Representative agent in the chat interface.

**Sarah's Question** (exactly as written):
*"Hi, I'm a customer service rep at Horizon Community Bank. A business owner just came in with a loan application for $250,000. The business is called 'Tech Solutions LLC' and they want to expand their operations. What should I do first?"*

**Sarah's MCP Demo** (after initial response):
*"Now let me show you how the agent can access our live database. Let me ask it to check for any existing records for this business."*

**Sarah's MCP Question**:
*"Can you search the database for any existing records for Tech Solutions LLC?"*

**Sarah's Transition** (after agent responds):
*"Perfect! The agent provided clear documentation requirements and procedures, plus it can access our live database. Now, as we process this application, our system has identified some potential red flags that require investigation. Let me hand this over to Marcus, our Compliance Officer."*

---

#### **🔍 Stage 2: Fraud Detection & Compliance Investigation (2-3 minutes) - Marcus Rodriguez**

**Marcus's Introduction:**
*"Thank you, Sarah. I'm Marcus Rodriguez, Compliance & Risk Officer. When our system flags potential risks, our AML Investigator agent helps us conduct thorough due diligence. This agent can access both our compliance procedures and query our database for suspicious patterns."*

**Action**: Marcus switches to AML Investigator agent in the chat interface.

**Marcus's Question** (exactly as written):
*"I'm reviewing the Tech Solutions LLC loan application. The business was incorporated only 3 months ago, but they're requesting $250,000. The owner has no prior banking history with us, and the business address is a residential property. What red flags should I investigate?"*

**Marcus's MCP Demo** (after initial response):
*"Let me show you how the agent can query our database for suspicious patterns."*

**Marcus's MCP Question**:
*"Search the database for any records related to Red Flag Business or similar high-risk applications."*

**Marcus's Transition** (after agent responds):
*"Excellent! The agent identified specific compliance risks and investigation steps, plus it can access our live database for pattern analysis. Now that we have a clear risk assessment, let me pass this to Jennifer, our Senior Commercial Lender, for the final credit decision."*

---

#### **💰 Stage 3: Credit Decision & Loan Structuring (2-3 minutes) - Jennifer Park**

**Jennifer's Introduction:**
*"Thank you, Marcus. I'm Jennifer Park, Senior Commercial Lender. Even with identified risks, we need to make informed credit decisions. Our Commercial Loan Officer agent helps us balance risk with opportunity by accessing both our lending guidelines and historical loan data."*

**Action**: Jennifer switches to Commercial Loan Officer agent in the chat interface.

**Jennifer's Question** (exactly as written):
*"I'm the commercial loan officer reviewing the Tech Solutions LLC application. The fraud team has flagged some concerns, but the business plan looks solid. They have a $50,000 deposit and good credit score. What factors should I consider for approval, and what additional documentation should I request?"*

**Jennifer's MCP Demo** (after initial response):
*"Let me show you how the agent can analyze historical loan data to inform our decision."*

**Jennifer's MCP Question**:
*"Search the database for similar loan applications and show me the approval patterns."*

**Jennifer's Analysis** (after agent responds):
*"Perfect! The agent provided comprehensive credit analysis and risk mitigation strategies, plus it can access our historical loan data for informed decision-making. This demonstrates how our AI platform enables data-driven decisions while maintaining compliance."*

---

### **Closing (1-2 minutes) - Sarah Chen**

**Sarah's Summary:**
*"Thank you, team! This demo shows the power of our AI Virtual Agent platform in real-world banking scenarios. We've seen how three specialized agents work together seamlessly:*

- *Customer Service ensures professional, efficient processing with live database access*
- *AML Investigation maintains regulatory compliance and risk management with pattern analysis*
- *Commercial Lending enables informed credit decisions using historical data*

*The result is faster, more accurate decision-making, improved compliance, and better customer service. Each agent brings specialized expertise while maintaining consistency across our banking operations. The integration of both knowledge bases and live database access through MCP servers gives our agents comprehensive capabilities. This is how AI transforms banking workflows."*

### **Key Demo Highlights**

 **Logical Workflow**: Customer Service → Compliance → Credit Decision  
 **Realistic Scenario**: Tech Solutions LLC loan application  
 **Clear Transitions**: Each presenter hands off to the next  
 **Business Value**: Shows operational efficiency and risk management  
 **Technical Capabilities**: Demonstrates agent specialization, RAG integration, and MCP database access

---

## 🔧 Troubleshooting

### **If Agents Don't Respond**
- [ ] Check if agents are properly deployed
- [ ] Verify knowledge bases are in "READY" status
- [ ] Ensure MCP server is connected and active
- [ ] Verify you're using the correct agent in chat

### **If Responses Are Poor**
- [ ] Verify knowledge bases contain the banking documents
- [ ] Check if agents have access to the correct knowledge base IDs
- [ ] Ensure template was updated with both RAG and MCP tool configuration
- [ ] Test MCP server connection separately

### **If MCP Database Queries Fail**
- [ ] Verify MCP server is running and accessible
- [ ] Check if database contains test data
- [ ] Ensure agent has MCP tools configured
- [ ] Test with simple database queries first

### **If Demo Questions Don't Work**
- [ ] Use the exact questions provided above
- [ ] Check if agents are responding to simpler questions first
- [ ] Verify the demo scenario makes sense for the audience
- [ ] Test MCP functionality separately before the demo

---

## 📋 Success Indicators

### **Good Demo Signs**
-  Agents provide specific, banking-relevant responses
-  Responses include current procedures and compliance requirements
-  Each agent demonstrates specialized knowledge
-  MCP database queries return relevant information
-  Audience recognizes the banking workflow
-  Integration between RAG and MCP is seamless

### **Demo Flow Success**
-  Smooth transition between agents
-  Each step builds on the previous one
-  Business value is clear and impactful
-  Technical capabilities are naturally demonstrated
-  Both knowledge base and database access work smoothly

---

## 🎯 Key Points to Emphasize

### **Business Value**
- **Operational Efficiency**: Immediate access to information and live data
- **Risk Management**: Proactive compliance and risk assessment with real-time data
- **Customer Experience**: Professional, accurate service with comprehensive information
- **Regulatory Compliance**: No missed requirements or deadlines
- **Data-Driven Decisions**: Access to both procedural knowledge and historical data

### **Technical Capabilities (Subtle)**
- **RAG Integration**: Knowledge base access for procedures and guidelines
- **MCP Integration**: Live database access for real-time information
- **Agent Specialization**: Different agents for different banking roles
- **Seamless Integration**: Both RAG and MCP work together naturally
- **Scalable Architecture**: Easy to add new tools and capabilities 