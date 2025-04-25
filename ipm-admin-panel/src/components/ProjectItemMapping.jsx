import React, { useState, useEffect } from 'react';
import { assignItemToProject, getProjectItems, getAllProjects, getAllItems } from '../services/api';

const ProjectItemMapping = ({ token }) => {
  const [selectedItemIds, setSelectedItemIds] = useState([]); // Changed to array
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [projectItems, setProjectItems] = useState([]);
  const [projects, setProjects] = useState([]);
  const [items, setItems] = useState([]);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const handleAssign = async () => {
    if (selectedItemIds.length === 0 || !selectedProjectId) return;
    setMessage('');
    setLoading(true);
    try {
      // Assign each selected item to the project
      for (const itemId of selectedItemIds) {
        await assignItemToProject(itemId, selectedProjectId, token);
      }
      setMessage('Items assigned to project successfully');
      fetchProjectItems(selectedProjectId);
      setSelectedItemIds([]); // Clear selection after successful assignment
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleItemChange = (event) => {
    const selectedOptions = Array.from(event.target.selectedOptions).map(option => option.value);
    setSelectedItemIds(selectedOptions);
  };

  const fetchProjectItems = async (projectId) => {
    if (!projectId) return;
    try {
      const response = await getProjectItems(projectId, token);
      setProjectItems(response.data || []);
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

  const fetchAllItems = async () => {
    try {
      const response = await getAllItems(token);
      setItems(response.data || []);
    } catch (error) {
      setMessage(error.message);
    }
  };

  useEffect(() => {
    fetchAllProjects();
    fetchAllItems();
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      fetchProjectItems(selectedProjectId);
    } else {
      setProjectItems([]);
    }
  }, [selectedProjectId]);

  return (
    <div className="mapping-form">
      <h3>Assign Items to Project</h3>
      <div>
        <label>Items:</label>
        <select 
          multiple 
          value={selectedItemIds}
          onChange={handleItemChange}
          style={{ height: '150px' }}
        >
          {items.map((item) => (
            <option key={item.uuid} value={item.uuid}>
              {item.name} - {item.category || 'No Category'}
            </option>
          ))}
        </select>
        <small style={{ display: 'block', marginTop: '5px' }}>Hold Ctrl/Cmd to select multiple items</small>
      </div>
      <div>
        <label>Project:</label>
        <select 
          value={selectedProjectId} 
          onChange={(e) => setSelectedProjectId(e.target.value)}
          disabled={loading}
        >
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
        disabled={selectedItemIds.length === 0 || !selectedProjectId || loading}
      >
        {loading ? 'Assigning...' : 'Assign'}
      </button>
      {message && <p className={message.includes('success') ? 'success' : 'error'}>{message}</p>}
      
      <div className="mapping-list">
        <h4>Project's Items</h4>
        {projectItems.length > 0 ? (
          <ul>
            {projectItems.map((item) => (
              <li key={item.uuid}>
                {item.name} - Category: {item.category || 'No Category'}
              </li>
            ))}
          </ul>
        ) : (
          <p>No items assigned to this project</p>
        )}
      </div>

      <style jsx>{`
        .mapping-form {
          max-width: 600px;
          margin: 0 auto;
          padding: 20px;
        }

        .mapping-form div {
          margin-bottom: 15px;
        }

        label {
          display: block;
          margin-bottom: 5px;
          font-weight: 500;
        }

        select {
          width: 100%;
          padding: 8px;
          border: 1px solid #ccc;
          border-radius: 4px;
        }

        select[multiple] {
          min-height: 150px;
        }

        button {
          padding: 8px 16px;
          background-color: #0066cc;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
        }

        button:disabled {
          background-color: #cccccc;
          cursor: not-allowed;
        }

        .success {
          color: green;
          margin: 10px 0;
        }

        .error {
          color: red;
          margin: 10px 0;
        }

        small {
          color: #666;
        }

        ul {
          list-style: none;
          padding: 0;
        }

        li {
          padding: 8px;
          border-bottom: 1px solid #eee;
        }

        li:last-child {
          border-bottom: none;
        }
      `}</style>
    </div>
  );
};

export default ProjectItemMapping;
