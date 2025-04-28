import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getProjectUsers, getProjectItems, getProjectInfo, assignUserToProject, assignItemToProject, getAllUsers, getAllItems } from '../services/api';
import UserCreate from './UserCreate';
import ItemCreate from './ItemCreate';
import '../styles/ProjectDetails.css';

const ProjectDetails = ({ projectId, token }) => {
  const [users, setUsers] = useState([]);
  const [items, setItems] = useState([]);
  const [allUsers, setAllUsers] = useState([]);
  const [allItems, setAllItems] = useState([]);
  const [projectName, setProjectName] = useState('');
  const [projectDescription, setProjectDescription] = useState('');
  const [projectLocation, setProjectLocation] = useState('');
  const [poBalance, setPoBalance] = useState(null);
  const [estimatedBalance, setEstimatedBalance] = useState(null);
  const [actualBalance, setActualBalance] = useState(null);
  const [poDocumentPath, setPoDocumentPath] = useState(null);
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
      setProjectLocation(data.location || '');
      setPoBalance(data.po_balance !== undefined ? data.po_balance : null);
      setEstimatedBalance(data.estimated_balance !== undefined ? data.estimated_balance : null);
      setActualBalance(data.actual_balance !== undefined ? data.actual_balance : null);
      setPoDocumentPath(data.po_document_path || null);
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
          <li><strong>Location:</strong> {projectLocation || 'N/A'}</li>
          <li><strong>PO Balance:</strong> {poBalance !== null ? poBalance : 'N/A'}</li>
          <li><strong>Estimated Balance:</strong> {estimatedBalance !== null ? estimatedBalance : 'N/A'}</li>
          <li><strong>Actual Balance:</strong> {actualBalance !== null ? actualBalance : 'N/A'}</li>
          {poDocumentPath && (
            <li>
              <strong>PO Document:</strong>{' '}
              <a href={poDocumentPath} target="_blank" rel="noopener noreferrer">View Document</a>
            </li>
          )}
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
              className="assign-button"
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
                className="assign-button"
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
    </div>
  );
};

export default ProjectDetails;
