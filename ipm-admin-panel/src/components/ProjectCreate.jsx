import React, { useState } from 'react';
import { createProject } from '../services/api';

const ProjectCreate = ({ token }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [location, setLocation] = useState('');
  const [balance, setBalance] = useState('');
  const [message, setMessage] = useState('');

  const handleCreate = async () => {
    setMessage('');
    if (!name) {
      setMessage('Project name is required');
      return;
    }
    try {
      const projectData = {
        name,
        description,
        location,
        balance: balance ? parseFloat(balance) : 0.0,
      };
      await createProject(projectData, token);
      setMessage('Project created successfully');
      setName('');
      setDescription('');
      setLocation('');
      setBalance('');
    } catch (error) {
      setMessage(error.message);
    }
  };

  return (
    <div>
      <h3>Create New Project</h3>
      <div>
        <label>Name:</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Project Name"
        />
      </div>
      <div>
        <label>Description:</label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Project Description"
        />
      </div>
      <div>
        <label>Location:</label>
        <input
          type="text"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          placeholder="Project Location"
        />
      </div>
      <div>
        <label>Initial Balance:</label>
        <input
          type="number"
          value={balance}
          onChange={(e) => setBalance(e.target.value)}
          placeholder="Initial Balance"
          step="0.01"
          min="0"
        />
      </div>
      <button onClick={handleCreate}>Create Project</button>
      {message && <p>{message}</p>}
    </div>
  );
};

export default ProjectCreate;
