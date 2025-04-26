import React, { useState, useEffect } from 'react';
import { assignItemToProject, getProjectItems, getAllProjects, getAllItems } from '../services/api';

const ProjectItemMapping = ({ token }) => {
  const [selectedItemIds, setSelectedItemIds] = useState([]); 
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [projectItems, setProjectItems] = useState([]);
  const [projects, setProjects] = useState([]);
  const [items, setItems] = useState([]);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [itemBalances, setItemBalances] = useState({});

  const handleAssign = async () => {
    if (selectedItemIds.length === 0 || !selectedProjectId) return;
    setMessage('');
    setLoading(true);
    try {
      // Assign each selected item to the project with its balance
      for (const itemId of selectedItemIds) {
        await assignItemToProject(itemId, selectedProjectId, itemBalances[itemId] || 0, token);
      }
      setMessage('Items assigned to project successfully');
      fetchProjectItems(selectedProjectId);
      setSelectedItemIds([]); // Clear selection after successful assignment
      setItemBalances({}); // Clear balances
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleItemChange = (event) => {
    const selectedOptions = Array.from(event.target.selectedOptions).map(option => option.value);
    setSelectedItemIds(selectedOptions);
    
    // Initialize balances for newly selected items
    const newBalances = { ...itemBalances };
    selectedOptions.forEach(itemId => {
      if (!newBalances[itemId]) {
        newBalances[itemId] = 0;
      }
    });
    setItemBalances(newBalances);
  };

  const handleBalanceChange = (itemId, value) => {
    setItemBalances(prev => ({
      ...prev,
      [itemId]: parseFloat(value) || 0
    }));
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

      {selectedItemIds.length > 0 && (
        <div className="selected-items-balances">
          <h4>Set Balance for Selected Items:</h4>
          {selectedItemIds.map(itemId => {
            const item = items.find(i => i.uuid === itemId);
            return (
              <div key={itemId} className="balance-input-row">
                <label>{item?.name}:</label>
                <input
                  type="number"
                  value={itemBalances[itemId] || 0}
                  onChange={(e) => handleBalanceChange(itemId, e.target.value)}
                  placeholder="Enter balance"
                  step="0.01"
                  min="0"
                  disabled={loading}
                />
              </div>
            );
          })}
        </div>
      )}

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
                {item.name} - {item.category || 'No Category'} 
                {item.item_balance !== undefined && (
                  <span className="item-balance"> (Balance: {item.item_balance})</span>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p>No items assigned to this project yet</p>
        )}
      </div>

      <style jsx>{`
        .mapping-form {
          padding: 20px;
          max-width: 600px;
          margin: 0 auto;
        }
        .balance-input-row {
          display: flex;
          align-items: center;
          margin: 10px 0;
          gap: 10px;
        }
        .balance-input-row label {
          min-width: 150px;
        }
        .balance-input-row input {
          width: 120px;
          padding: 5px;
        }
        .selected-items-balances {
          margin: 20px 0;
          padding: 15px;
          border: 1px solid #ddd;
          border-radius: 4px;
        }
        .item-balance {
          color: #666;
          margin-left: 10px;
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
