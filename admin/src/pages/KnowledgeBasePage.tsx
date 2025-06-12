import React, { useEffect, useState } from 'react';
import axios from '../api/axios';

interface KnowledgeBase {
  id?: string;
  name: string;
  provider_id?: string;
  type?: string;
  embedding_model?: string;
  version?: string;
  vector_db_name?: string;
  is_external?: boolean;
  source?: string;
  source_configuration?: any;
}

export default function KnowledgeBasePage() {
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [form, setForm] = useState<KnowledgeBase>({
    name: '',
    provider_id: '',
    type: '',
    embedding_model: '',
    version: '',
    vector_db_name: '',
    is_external: false,
    source: '',
    source_configuration: {},
  });

  const [s3Inputs, setS3Inputs] = useState({
    ACCESS_KEY_ID: '',
    SECRET_ACCESS_KEY: '',
    ENDPOINT_URL: '',
    BUCKET_NAME: '',
    REGION: '',
  });

  const [githubInputs, setGithubInputs] = useState({
    url: '',
    path: '',
    token: '',
    branch: '',
  });

  const [urlInputs, setUrlInputs] = useState<string[]>(['']);

  useEffect(() => {
    fetchKbs();
  }, []);

  useEffect(() => {
    if (form.source === 'S3') {
      const sourceConfig = JSON.stringify(s3Inputs, null, 2);
      setForm((f) => ({ ...f, source_configuration: sourceConfig }));
    } else if (form.source === 'GITHUB') {
      const sourceConfig = JSON.stringify(githubInputs, null, 2);
      setForm((f) => ({ ...f, source_configuration: sourceConfig }));
    } else if (form.source === 'URL') {
      const sourceConfig = JSON.stringify(urlInputs.filter(Boolean), null, 2);
      setForm((f) => ({ ...f, source_configuration: sourceConfig }));
    }
  }, [s3Inputs, githubInputs, urlInputs, form.source]);

  const fetchKbs = async () => {
    const res = await axios.get('/knowledge_bases');
    setKbs(res.data);
  };

  const handleSubmit = async () => {
    try {
      const parsedConfig = JSON.parse(form.source_configuration || '{}');
      const payload = { ...form, source_configuration: parsedConfig };
      await axios.post('/knowledge_bases', payload);
      setForm({
        name: '',
        version: '',
        embedding_model: '',
        provider_id: '',
        vector_db_name: '',
        is_external: false,
        source: '',
        source_configuration: '{}',
      });
      setS3Inputs({
        ACCESS_KEY_ID: '',
        SECRET_ACCESS_KEY: '',
        ENDPOINT_URL: '',
        BUCKET_NAME: '',
        REGION: '',
      });
      setGithubInputs({ url: '', path: '', token: '', branch: '' });
      setUrlInputs(['']);
      fetchKbs();
    } catch (err) {
      alert('Invalid JSON in source configuration field.');
    }
  };

  const handleDelete = async (id: string) => {
    await axios.delete(`/knowledge_bases/${id}`);
    fetchKbs();
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">Knowledge Bases</h1>

      <div className="bg-white shadow rounded p-4 space-y-3 mb-6">
        <input
          className="w-full border p-2 rounded"
          placeholder="Name"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
        />
        <input
          className="w-full border p-2 rounded"
          placeholder="Version"
          value={form.version}
          onChange={(e) => setForm({ ...form, version: e.target.value })}
        />
        <input
          className="w-full border p-2 rounded"
          placeholder="Embedding Model"
          value={form.embedding_model}
          onChange={(e) => setForm({ ...form, embedding_model: e.target.value })}
        />
        <input
          className="w-full border p-2 rounded"
          placeholder="Provider ID"
          value={form.provider_id}
          onChange={(e) => setForm({ ...form, provider_id: e.target.value })}
        />
        <input
          className="w-full border p-2 rounded"
          placeholder="Vector DB Name"
          value={form.vector_db_name}
          onChange={(e) => setForm({ ...form, vector_db_name: e.target.value })}
        />
        <label className="inline-flex items-center space-x-2">
          <input
            type="checkbox"
            checked={form.is_external}
            onChange={(e) => setForm({ ...form, is_external: e.target.checked })}
          />
          <span>External</span>
        </label>
        <select
          className="w-full border p-2 rounded"
          value={form.source}
          onChange={(e) => setForm({ ...form, source: e.target.value })}
          disabled={form.is_external}
        >
          <option value="">Select Source</option>
          <option value="S3">S3</option>
          <option value="GITHUB">GitHub</option>
          <option value="URL">URL</option>
        </select>

        {form.source === 'S3' && !form.is_external && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input
              className="border p-2 rounded"
              placeholder="ACCESS_KEY_ID"
              value={s3Inputs.ACCESS_KEY_ID}
              onChange={(e) => setS3Inputs({ ...s3Inputs, ACCESS_KEY_ID: e.target.value })}
            />
            <input
              className="border p-2 rounded"
              placeholder="SECRET_ACCESS_KEY"
              value={s3Inputs.SECRET_ACCESS_KEY}
              onChange={(e) => setS3Inputs({ ...s3Inputs, SECRET_ACCESS_KEY: e.target.value })}
            />
            <input
              className="border p-2 rounded"
              placeholder="ENDPOINT_URL"
              value={s3Inputs.ENDPOINT_URL}
              onChange={(e) => setS3Inputs({ ...s3Inputs, ENDPOINT_URL: e.target.value })}
            />
            <input
              className="border p-2 rounded"
              placeholder="BUCKET_NAME"
              value={s3Inputs.BUCKET_NAME}
              onChange={(e) => setS3Inputs({ ...s3Inputs, BUCKET_NAME: e.target.value })}
            />
            <input
              className="border p-2 rounded"
              placeholder="REGION"
              value={s3Inputs.REGION}
              onChange={(e) => setS3Inputs({ ...s3Inputs, REGION: e.target.value })}
            />
          </div>
        )}

        {form.source === 'GITHUB' && !form.is_external && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input
              className="border p-2 rounded"
              placeholder="URL"
              value={githubInputs.url}
              onChange={(e) => setGithubInputs({ ...githubInputs, url: e.target.value })}
            />
            <input
              className="border p-2 rounded"
              placeholder="Path"
              value={githubInputs.path}
              onChange={(e) => setGithubInputs({ ...githubInputs, path: e.target.value })}
            />
            <input
              className="border p-2 rounded"
              placeholder="Token"
              value={githubInputs.token}
              onChange={(e) => setGithubInputs({ ...githubInputs, token: e.target.value })}
            />
            <input
              className="border p-2 rounded"
              placeholder="Branch"
              value={githubInputs.branch}
              onChange={(e) => setGithubInputs({ ...githubInputs, branch: e.target.value })}
            />
          </div>
        )}

        {form.source === 'URL' && !form.is_external && (
          <div className="space-y-2">
            {urlInputs.map((url, index) => (
              <div key={index} className="flex items-center space-x-2">
                <input
                  className="flex-grow border p-2 rounded"
                  placeholder={`URL ${index + 1}`}
                  value={url}
                  onChange={(e) => {
                    const updated = [...urlInputs];
                    updated[index] = e.target.value;
                    setUrlInputs(updated);
                  }}
                />
                <button
                  className="text-red-600 hover:underline"
                  onClick={() => {
                    const updated = urlInputs.filter((_, i) => i !== index);
                    setUrlInputs(updated);
                  }}
                  disabled={urlInputs.length === 1}
                >
                  Remove
                </button>
              </div>
            ))}
            <button
              className="mt-2 text-blue-600 hover:underline"
              onClick={() => setUrlInputs([...urlInputs, ''])}
            >
              + Add URL
            </button>
          </div>
        )}

        <textarea
          className="w-full border p-2 rounded"
          placeholder="Source Configuration (JSON format)"
          value={form.source_configuration}
          onChange={(e) => setForm({ ...form, source_configuration: e.target.value })}
          rows={4}
          disabled={
            form.is_external ||
            form.source === 'S3' ||
            form.source === 'GITHUB' ||
            form.source === 'URL'
          }
        />
        <button
          onClick={handleSubmit}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          Create
        </button>
      </div>

      <ul className="space-y-3">
        {kbs.map((kb) => (
          <li
            key={kb.id}
            className="bg-white p-4 rounded shadow-sm border flex justify-between items-center"
          >
            <div>
              <strong>{kb.name}</strong>{' '}
              <span className="text-sm text-gray-600">v{kb.version}</span>
              <p className="text-sm text-gray-600">Model: {kb.embedding_model}</p>
              <p className="text-sm text-gray-600">Vector DB: {kb.vector_db_name}</p>
              <p className="text-sm text-gray-500">Source: {kb.source}</p>
              <pre className="text-xs text-gray-500 whitespace-pre-wrap">
                {JSON.stringify(kb.source_configuration, null, 2)}
              </pre>
            </div>
            <div className="space-x-2">
              <button onClick={() => handleDelete(kb.id!)} className="text-red-600 hover:underline">
                Delete
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
