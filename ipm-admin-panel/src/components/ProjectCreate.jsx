import React, { useState, useRef } from 'react';
import { createProject } from '../services/api';
import '../styles/ProjectCreate.css';

const ProjectCreate = ({ token, onClose }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [location, setLocation] = useState('');
  const [poBalance, setPoBalance] = useState('');
  const [estimatedBalance, setEstimatedBalance] = useState('');
  const [poDocument, setPoDocument] = useState(null);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef(null);

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
        actual_balance: 0.0
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
      setPoDocument(null);

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

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="create-project-form">
      <h3>Create New Project</h3>
      <div className="form-group">
        <label>Project Name *</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Enter project name"
          disabled={loading}
          required
        />
      </div>
      <div className="form-group">
        <label>Description</label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Enter project description"
          disabled={loading}
        />
      </div>
      <div className="form-group">
        <label>Location</label>
        <input
          type="text"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          placeholder="Enter project location"
          disabled={loading}
        />
      </div>
      <div className="form-group">
        <label>PO Balance</label>
        <div className="po-balance-group">
          <div className="po-balance-input">
            <input
              type="number"
              value={poBalance}
              onChange={(e) => setPoBalance(e.target.value)}
              placeholder="Enter PO balance"
              step="0.01"
              min="0"
              disabled={loading}
            />
          </div>
          {poBalance > 0 && (
            <div className="upload-button" onClick={triggerFileInput} title={poDocument ? 'Change PO Document' : 'Upload PO Document'}>
              <label className="upload-label">
                <svg className="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path d="M12 5v14M5 12h14" strokeWidth="2" strokeLinecap="round"/>
                </svg>
              </label>
              <input
                ref={fileInputRef}
                type="file"
                onChange={handleFileChange}
                accept=".pdf,.doc,.docx"
                disabled={loading}
              />
            </div>
          )}
        </div>
        {poDocument && (
          <small className="help-text">Selected file: {poDocument.name}</small>
        )}
        {poBalance > 0 && !poDocument && (
          <small className="help-text">Optional: Upload PO document for verification</small>
        )}
      </div>
      <div className="form-group">
        <label>Estimated Balance</label>
        <input
          type="number"
          value={estimatedBalance}
          onChange={(e) => setEstimatedBalance(e.target.value)}
          placeholder="Enter estimated balance"
          step="0.01"
          min="0"
          disabled={loading}
        />
      </div>
      <button 
        className="submit-button" 
        onClick={handleCreate} 
        disabled={loading}
      >
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
