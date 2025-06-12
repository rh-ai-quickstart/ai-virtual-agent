import React, { useEffect, useState } from 'react';
import axios from '../api/axios';
import { Link } from 'react-router-dom';

interface VirtualAssistant {
  id: string;
  name: string;
  model_name: string;
  prompt: string;
}

interface MCPServer {
  id: string;
  name: string;
  title: string;
}

interface KnowledgeBase {
  id: string;
  name: string;
  version: string;
}

interface ModelServer {
  id: string;
  name: string;
  model_type: string;
}

export default function Dashboard() {
  const [assistants, setAssistants] = useState<VirtualAssistant[]>([]);
  const [mcps, setMcps] = useState<MCPServer[]>([]);
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [models, setModels] = useState<ModelServer[]>([]);

  useEffect(() => {
    fetchAll();
  }, []);

  const fetchAll = async () => {
    const [a, m, k, s] = await Promise.all([
      axios.get('/virtual_assistants'),
      axios.get('/mcp_servers'),
      axios.get('/knowledge_bases'),
      axios.get('/model_servers')
    ]);
    setAssistants(a.data);
    setMcps(m.data);
    setKbs(k.data);
    setModels(s.data);
  };

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-10">
      <h1 className="text-3xl font-bold text-center">🧠 Virtual Agent Dashboard</h1>

      <section className="bg-white rounded-xl shadow p-5">
        <h2 className="text-xl font-semibold mb-4 border-b pb-2">Virtual Assistants</h2>
        <ul className="grid md:grid-cols-2 gap-4">
          {assistants.map(agent => (
            <li key={agent.id} className="border rounded-lg p-4 shadow-sm bg-gray-50 hover:shadow-md transition">
              <h3 className="font-semibold text-lg mb-1">{agent.name}</h3>
              <p className="text-sm text-gray-600">Model: {agent.model_name}</p>
              <p className="text-sm italic text-gray-500 truncate">Prompt: {agent.prompt.slice(0, 100)}...</p>

            </li>
          ))}
          <Link to={`/virtual_assistants`} className="text-blue-600 hover:underline text-sm mt-2 inline-block">Manage</Link>
        </ul>
      </section>

      <section className="bg-white rounded-xl shadow p-5">
        <h2 className="text-xl font-semibold mb-4 border-b pb-2">MCP Servers</h2>
        <ul className="space-y-2">
          {mcps.map(server => (
            <li key={server.id} className="bg-gray-50 p-3 rounded shadow-sm hover:bg-gray-100">
              <strong>{server.name}</strong> — <span className="text-gray-700">{server.title}</span>
            </li>
          ))}
        </ul>
        <Link to="/mcp_servers" className="text-blue-600 hover:underline text-sm mt-2 inline-block">Manage MCP Servers</Link>
      </section>

      <section className="bg-white rounded-xl shadow p-5">
        <h2 className="text-xl font-semibold mb-4 border-b pb-2">Knowledge Bases</h2>
        <ul className="space-y-2">
          {kbs.map(kb => (
            <li key={kb.id} className="bg-gray-50 p-3 rounded shadow-sm hover:bg-gray-100">
              <strong>{kb.name}</strong> <span className="text-sm text-gray-600">(v{kb.version})</span>
            </li>
          ))}
        </ul>
        <Link to="/knowledge_bases" className="text-blue-600 hover:underline text-sm mt-2 inline-block">Manage Knowledge Bases</Link>
      </section>

      <section className="bg-white rounded-xl shadow p-5">
        <h2 className="text-xl font-semibold mb-4 border-b pb-2">Model Servers</h2>
        <ul className="space-y-2">
          {models.map(model => (
            <li key={model.id} className="bg-gray-50 p-3 rounded shadow-sm hover:bg-gray-100">
              <strong>{model.name}</strong> — <span className="text-gray-700">{model.model_type}</span>
            </li>
          ))}
        </ul>
        <Link to="/model_servers" className="text-blue-600 hover:underline text-sm mt-2 inline-block">Manage Model Servers</Link>
      </section>

      <section className="bg-white rounded-xl shadow p-5">
        <h2 className="text-xl font-semibold mb-4 border-b pb-2">Chat Interface</h2>
        <p className="text-gray-600 mb-4">Test and interact with LlamaStack models through the chat interface.</p>
        <Link to="/chat" className="text-blue-600 hover:underline text-sm mt-2 inline-block">Open Chat Interface</Link>
      </section>
    </div>
  );
}
