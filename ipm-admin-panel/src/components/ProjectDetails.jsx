import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getProjectUsers, getProjectItems, getProjectInfo, assignUserToProject, assignItemToProject, getAllUsers, getAllItems } from '../services/api';
import UserCreate from './UserCreate';
import ItemCreate from './ItemCreate';

const ProjectDetails = ({ projectId, token }) => {
  const [users, setUsers] = useState([]);
  const [items, setItems] = useState([]);
  const [allUsers, setAllUsers] = useState([]);
  const [allItems, setAllItems] = useState([]);
  const [projectName, setProjectName] = useState('');
  const [projectDescription, setProjectDescription] = useState('');
  const [projectBalance, setProjectBalance] = useState(null);
  const [message, setMessage] = useState('');
  const [selectedUser, setSelectedUser] = useState('');
  const [selectedItems, setSelectedItems] = useState([]);
  const [itemBalances, setItemBalances] = useState({});
  const [loading, setLoading] = useState(false);
  const [showCreateUser, setShowCreateUser] = useState(false);
  const [showCreateItem, setShowCreateItem] = useState(false);
  const navigate = useNavigate();

  const fetchProjectUsers = async () => {
    try {
      const response = await getProjectUsers(projectId, token);
      setUsers(response.data || []);
    } catch (error) {
      setMessage(error.message);
    }
  };

  const fetchProjectItems = async () => {
    try {
      const response = await getProjectItems(projectId, token);
      setItems(response.data || []);
    } catch (error) {
      setMessage(error.message);
    }
  };

  const fetchProjectInfo = async () => {
    try {
      const response = await getProjectInfo(projectId, token);
      const data = response.data || {};
      setProjectName(data.name || '');
      setProjectDescription(data.description || '');
      setProjectBalance(data.balance !== undefined ? data.balance : null);
    } catch (error) {
      setMessage(error.message);
    }
  };

  const fetchAllUsersAndItems = async () => {
    try {
      const [usersResponse, itemsResponse] = await Promise.all([
        getAllUsers(token),
        getAllItems(token)
      ]);
      setAllUsers(usersResponse.data || []);
      setAllItems(itemsResponse.data || []);
    } catch (error) {
      setMessage(error.message);
    }
  };

  const handleAssignUser = async () => {
    if (!selectedUser) return;
    setLoading(true);
    try {
      await assignUserToProject(selectedUser, projectId, token);
      setMessage('User assigned successfully');
      await fetchProjectUsers();
      setSelectedUser('');
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleItemChange = (event) => {
    const selectedOptions = Array.from(event.target.selectedOptions).map(option => option.value);
    setSelectedItems(selectedOptions);
    
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

  const handleAssignItems = async () => {
    if (selectedItems.length === 0) return;
    setLoading(true);
    try {
      for (const itemId of selectedItems) {
        await assignItemToProject(itemId, projectId, itemBalances[itemId] || 0, token);
      }
      setMessage('Items assigned successfully');
      await fetchProjectItems();
      setSelectedItems([]);
      setItemBalances({});
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleUserCreated = async () => {
    setShowCreateUser(false);
    await fetchAllUsersAndItems();
    setMessage('User created successfully');
  };

  const handleItemCreated = async () => {
    setShowCreateItem(false);
    await fetchAllUsersAndItems();
    setMessage('Item created successfully');
  };

  const handleBackClick = () => {
    navigate('/admin-dashboard');
  };

  useEffect(() => {
    if (projectId) {
      fetchProjectUsers();
      fetchProjectItems();
      fetchProjectInfo();
      fetchAllUsersAndItems();
    }
  }, [projectId]);

  return (
    <div className="project-details">
      <div className="header">
        <button className="back-button" onClick={handleBackClick}>← Back to Dashboard</button>
        <h2>Project Details</h2>
      </div>

      {message && (
        <p className={message.includes('success') ? 'success-message' : 'error-message'}>
          {message}
        </p>
      )}
      
      <div className="project-info">
        <h4>Project Info</h4>
        <ul>
          <li><strong>Name:</strong> {projectName || 'N/A'}</li>
          <li><strong>Description:</strong> {projectDescription || 'N/A'}</li>
          <li><strong>Balance:</strong> {projectBalance !== null ? projectBalance : 'N/A'}</li>
        </ul>
      </div>

      <div className="assign-section">
        <div className="assign-user">
          <h4>Assign New User</h4>
          <div className="assign-form">
            <select 
              value={selectedUser} 
              onChange={(e) => setSelectedUser(e.target.value)}
              disabled={loading}
            >
              <option value="">Select User</option>
              {allUsers
                .filter(user => !users.some(u => u.uuid === user.uuid))
                .map(user => (
                  <option key={user.uuid} value={user.uuid}>
                    {user.name} ({user.role})
                  </option>
                ))
              }
            </select>
            <button 
              onClick={handleAssignUser} 
              disabled={!selectedUser || loading}
            >
              {loading ? 'Assigning...' : 'Assign User'}
            </button>
            <button 
              onClick={() => setShowCreateUser(true)}
              className="create-new-btn"
            >
              Create New User
            </button>
          </div>
        </div>

        <div className="assign-item">
          <h4>Assign New Items</h4>
          <div className="assign-form">
            <select 
              multiple
              value={selectedItems}
              onChange={handleItemChange}
              style={{ height: '150px' }}
              disabled={loading}
            >
              {allItems
                .filter(item => !items.some(i => i.uuid === item.uuid))
                .map(item => (
                  <option key={item.uuid} value={item.uuid}>
                    {item.name} - {item.category || 'No Category'}
                  </option>
                ))
              }
            </select>
            <small style={{ display: 'block', marginTop: '5px' }}>Hold Ctrl/Cmd to select multiple items</small>

            {selectedItems.length > 0 && (
              <div className="selected-items-balances">
                <h4>Set Balance for Selected Items:</h4>
                {selectedItems.map(itemId => {
                  const item = allItems.find(i => i.uuid === itemId);
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

            <div className="button-group">
              <button 
                onClick={handleAssignItems} 
                disabled={selectedItems.length === 0 || loading}
              >
                {loading ? 'Assigning...' : 'Assign Items'}
              </button>
              <button 
                onClick={() => setShowCreateItem(true)}
                className="create-new-btn"
              >
                Create New Item
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="current-assignments">
        <div className="users-list">
          <h4>Users Assigned</h4>
          {users.length > 0 ? (
            <ul>
              {users.map((user) => (
                <li key={user.uuid}>
                  {user.name} ({user.role})
                </li>
              ))}
            </ul>
          ) : (
            <p>No users assigned</p>
          )}
        </div>

        <div className="items-list">
          <h4>Items Assigned</h4>
          {items.length > 0 ? (
            <ul>
              {items.map((item) => (
                <li key={item.uuid}>
                  {item.name} - {item.category || 'No Category'}
                  <span className="item-balance"> (Balance: {item.remaining_balance || 0})</span>
                </li>
              ))}
            </ul>
          ) : (
            <p>No items assigned</p>
          )}
        </div>
      </div>

      {/* Modals */}
      {showCreateUser && (
        <div className="modal">
          <div className="modal-content">
            <button className="modal-close" onClick={() => setShowCreateUser(false)}>×</button>
            <UserCreate 
              token={token} 
              onSuccess={handleUserCreated}
            />
          </div>
        </div>
      )}

      {showCreateItem && (
        <div className="modal">
          <div className="modal-content">
            <button className="modal-close" onClick={() => setShowCreateItem(false)}>×</button>
            <ItemCreate 
              token={token} 
              onClose={() => setShowCreateItem(false)}
              onItemCreated={handleItemCreated}
            />
          </div>
        </div>
      )}

      <style jsx>{`
        .project-details {
          padding: 20px;
          max-width: 800px;
          margin: 0 auto;
        }

        .header {
          display: flex;
          align-items: center;
          margin-bottom: 24px;
          gap: 16px;
        }

        .back-button {
          padding: 8px 16px;
          border: none;
          background:rgb(49, 147, 244);
          border-radius: 4px;
          cursor: pointer;
          font-weight: 500;
        }

        .back-button:hover {
          background:rgb(21, 111, 201);
        }

        .success-message {
          color: green;
          margin: 10px 0;
        }

        .error-message {
          color: red;
          margin: 10px 0;
        }

        .assign-section {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
          margin: 20px 0;
        }

        .assign-form {
          display: flex;
          gap: 10px;
          margin-top: 10px;
          flex-wrap: wrap;
        }

        select {
          flex: 1;
          padding: 8px;
          border-radius: 4px;
          border: 1px solid #ccc;
          min-width: 200px;
        }

        select[multiple] {
          min-height: 150px;
        }

        button {
          padding: 8px 16px;
          border-radius: 4px;
          border: none;
          background-color: #0066cc;
          color: white;
          cursor: pointer;
          white-space: nowrap;
        }

        button:disabled {
          background-color: #cccccc;
          cursor: not-allowed;
        }

        .create-new-btn {
          background-color: #28a745;
          margin-left: 10px;
        }

        .button-group {
          display: flex;
          gap: 10px;
          margin-top: 10px;
        }

        .current-assignments {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
          margin-top: 20px;
        }

        ul {
          list-style: none;
          padding: 0;
          margin: 0;
        }

        li {
          padding: 8px;
          border-bottom: 1px solid #eee;
        }

        li:last-child {
          border-bottom: none;
        }

        .modal {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background-color: rgba(0, 0, 0, 0.5);
          display: flex;
          justify-content: center;
          align-items: center;
          z-index: 1000;
        }

        .modal-content {
          background: white;
          padding: 20px;
          border-radius: 8px;
          max-width: 90%;
          max-height: 90vh;
          overflow-y: auto;
          position: relative;
        }

        .modal-close {
          position: absolute;
          top: 10px;
          right: 10px;
          background: none;
          border: none;
          font-size: 24px;
          cursor: pointer;
          color: #666;
        }

        .modal-close:hover {
          color: #000;
        }

        small {
          color: #666;
        }

        .balance-input-row {
          display: flex;
          align-items: center;
          margin: 10px 0;
          gap: 10px;
        }

        .balance-input-row label {
          min-width: 150px;
          font-weight: 500;
        }

        .balance-input-row input {
          width: 120px;
          padding: 5px;
          border: 1px solid #ccc;
          border-radius: 4px;
        }

        .selected-items-balances {
          margin: 20px 0;
          padding: 15px;
          border: 1px solid #ddd;
          border-radius: 4px;
          background-color: #f8f9fa;
        }

        .item-balance {
          color: #666;
          margin-left: 10px;
          font-size: 0.9em;
        }
      `}</style>
    </div>
  );
};

export default ProjectDetails;
