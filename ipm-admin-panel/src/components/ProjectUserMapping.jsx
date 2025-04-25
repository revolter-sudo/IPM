import React, { useState, useEffect } from 'react';
import { assignUserToProject, getUserProjects, getAllUsers, getAllProjects } from '../services/api';

const ProjectUserMapping = ({ token }) => {
  const [selectedUserIds, setSelectedUserIds] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [userProjects, setUserProjects] = useState([]);
  const [users, setUsers] = useState([]);
  const [projects, setProjects] = useState([]);
  const [message, setMessage] = useState('');

  const handleAssign = async () => {
    setMessage('');
    try {
      // Assign each selected user to the project
      for (const userId of selectedUserIds) {
        await assignUserToProject(userId, selectedProjectId, token);
      }
      setMessage('Users assigned to project successfully');
      // Fetch updated projects for the last selected user
      if (selectedUserIds.length > 0) {
        fetchUserProjects(selectedUserIds[selectedUserIds.length - 1]);
      }
    } catch (error) {
      setMessage(error.message);
    }
  };

  const fetchUserProjects = async (userId) => {
    if (!userId) return;
    try {
      const response = await getUserProjects(userId, token);
      setUserProjects(response.data || []);
    } catch (error) {
      setMessage(error.message);
    }
  };

  const fetchAllUsers = async () => {
    try {
      const response = await getAllUsers(token);
      setUsers(response.data || []);
    } catch (error) {
      setMessage(error.message);
    }
  };

  const fetchAllProjects = async () => {
    try {
      const response = await getAllProjects(token);
      setProjects(response.data || []);
    } catch (error) {
      setMessage(error.message);
    }
  };

  const handleUserChange = (event) => {
    const selectedOptions = Array.from(event.target.selectedOptions).map(option => option.value);
    setSelectedUserIds(selectedOptions);
  };

  useEffect(() => {
    fetchAllUsers();
    fetchAllProjects();
  }, []);

  useEffect(() => {
    if (selectedUserIds.length > 0) {
      fetchUserProjects(selectedUserIds[selectedUserIds.length - 1]);
    } else {
      setUserProjects([]);
    }
  }, [selectedUserIds]);

  return (
    <div className="mapping-form">
      <h3>Assign Users to Project</h3>
      <div>
        <label>Users:</label>
        <select 
          multiple 
          value={selectedUserIds} 
          onChange={handleUserChange}
          style={{ height: '150px' }}
        >
          {users.map((user) => (
            <option key={user.uuid} value={user.uuid}>
              {user.name} ({user.phone})
            </option>
          ))}
        </select>
        <small style={{ display: 'block', marginTop: '5px' }}>Hold Ctrl/Cmd to select multiple users</small>
      </div>
      <div>
        <label>Project:</label>
        <select value={selectedProjectId} onChange={(e) => setSelectedProjectId(e.target.value)}>
          <option value="">Select Project</option>
          {projects.map((project) => (
            <option key={project.uuid} value={project.uuid}>
              {project.name}
            </option>
          ))}
        </select>
      </div>
      <button 
        className="create-new-btn" 
        onClick={handleAssign} 
        disabled={selectedUserIds.length === 0 || !selectedProjectId}
      >
        Assign
      </button>
      {message && <p className={message.includes('success') ? 'success' : 'error'}>{message}</p>}
      
      <div className="mapping-list">
        <h4>Selected User's Projects</h4>
        {userProjects.length > 0 ? (
          <ul>
            {userProjects.map((project) => (
              <li key={project.uuid}>
                {project.name} - Balance: {project.balance}
              </li>
            ))}
          </ul>
        ) : (
          <p>No projects assigned to this user</p>
        )}
      </div>
    </div>
  );
};

export default ProjectUserMapping;
