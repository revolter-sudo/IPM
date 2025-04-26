import React, { useState } from 'react';
import { createProject } from '../services/api';

const ProjectCreate = ({ token, onClose }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [location, setLocation] = useState('');
  const [poBalance, setPoBalance] = useState('');
  const [estimatedBalance, setEstimatedBalance] = useState('');
  const [actualBalance, setActualBalance] = useState('');
  const [poDocument, setPoDocument] = useState(null);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const handleCreate = async () => {
    setMessage('');
    setLoading(true);
    
    if (!name) {
      setMessage('Project name is required');
      setLoading(false);
      return;
    }

    try {
      const formData = new FormData();
      const projectData = {
        name,
        description,
        location,
        po_balance: poBalance ? parseFloat(poBalance) : 0.0,
        estimated_balance: estimatedBalance ? parseFloat(estimatedBalance) : 0.0,
        actual_balance: actualBalance ? parseFloat(actualBalance) : 0.0
      };

      formData.append('request', JSON.stringify(projectData));
      if (poDocument) {
        formData.append('po_document', poDocument);
      }

      await createProject(formData, token);
      setMessage('Project created successfully');
      
      // Reset form
      setName('');
      setDescription('');
      setLocation('');
      setPoBalance('');
      setEstimatedBalance('');
      setActualBalance('');
      setPoDocument(null);

      // Close modal if provided
      if (onClose) {
        onClose();
      }
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setPoDocument(e.target.files[0]);
    }
  };

  return (
    <div className="create-project-form">
      <h3>Create New Project</h3>
      <div className="form-group">
        <label>Name:</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Project Name"
          disabled={loading}
          required
        />
      </div>
      <div className="form-group">
        <label>Description:</label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Project Description"
          disabled={loading}
        />
      </div>
      <div className="form-group">
        <label>Location:</label>
        <input
          type="text"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          placeholder="Project Location"
          disabled={loading}
        />
      </div>
      <div className="form-group">
        <label>PO Balance:</label>
        <input
          type="number"
          value={poBalance}
          onChange={(e) => setPoBalance(e.target.value)}
          placeholder="PO Balance"
          step="0.01"
          min="0"
          disabled={loading}
        />
      </div>
      <div className="form-group">
        <label>Estimated Balance:</label>
        <input
          type="number"
          value={estimatedBalance}
          onChange={(e) => setEstimatedBalance(e.target.value)}
          placeholder="Estimated Balance"
          step="0.01"
          min="0"
          disabled={loading}
        />
      </div>
      <div className="form-group">
        <label>Actual Balance:</label>
        <input
          type="number"
          value={actualBalance}
          onChange={(e) => setActualBalance(e.target.value)}
          placeholder="Actual Balance"
          step="0.01"
          min="0"
          disabled={loading}
        />
      </div>
      <div className="form-group">
        <label>PO Document:</label>
        <input
          type="file"
          onChange={handleFileChange}
          accept=".pdf,.doc,.docx"
          disabled={loading}
        />
      </div>
      <button onClick={handleCreate} disabled={loading}>
        {loading ? 'Creating...' : 'Create Project'}
      </button>
      {message && (
        <p className={message.includes('success') ? 'success-message' : 'error-message'}>
          {message}
        </p>
      )}
    </div>
  );
};

export default ProjectCreate;
