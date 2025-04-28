import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getUserDetails, assignUserToProject, assignItemToProject, getAllProjects, getAllItems } from '../services/api';
import ItemCreate from './ItemCreate';
import '../styles/UserDetails.css';

const UserDetails = ({ userId, token }) => {
  const [userDetails, setUserDetails] = useState(null);
  const [allProjects, setAllProjects] = useState([]);
  const [allItems, setAllItems] = useState([]);
  const [selectedProjects, setSelectedProjects] = useState([]);
  const [selectedItems, setSelectedItems] = useState([]);
  const [itemBalances, setItemBalances] = useState({});
  const [selectedProjectForItems, setSelectedProjectForItems] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [showCreateItem, setShowCreateItem] = useState(false);
  const navigate = useNavigate();

  const fetchUserDetails = async () => {
    try {
      const response = await getUserDetails(userId, token);
      setUserDetails(response.data);
    } catch (error) {
      setMessage(error.message);
    }
  };

  const fetchAllData = async () => {
    try {
      const [projectsResponse, itemsResponse] = await Promise.all([
        getAllProjects(token),
        getAllItems(token)
      ]);
      setAllProjects(projectsResponse.data || []);
      setAllItems(itemsResponse.data || []);
    } catch (error) {
      setMessage(error.message);
    }
  };

  const handleProjectChange = (event) => {
    const selectedOptions = Array.from(event.target.selectedOptions).map(option => option.value);
    setSelectedProjects(selectedOptions);
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

  const handleAssignProjects = async () => {
    if (selectedProjects.length === 0) return;
    setLoading(true);
    try {
      for (const projectId of selectedProjects) {
        await assignUserToProject(userId, projectId, token);
      }
      setMessage('Projects assigned successfully');
      await fetchUserDetails();
      setSelectedProjects([]);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAssignItems = async () => {
    if (!selectedProjectForItems || selectedItems.length === 0) return;
    setLoading(true);
    try {
      for (const itemId of selectedItems) {
        await assignItemToProject(itemId, selectedProjectForItems, itemBalances[itemId] || 0, token);
      }
      setMessage('Items assigned to project successfully');
      await fetchUserDetails();
      setSelectedItems([]);
      setItemBalances({});
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleBackClick = () => {
    navigate('/admin-dashboard');
  };

  const handleItemCreated = async () => {
    setShowCreateItem(false);
    await fetchAllData();
    setMessage('Item created successfully');
  };

  useEffect(() => {
    if (userId) {
      fetchUserDetails();
      fetchAllData();
    }
  }, [userId]);

  if (!userDetails) {
    return <div className="loading">Loading user details...</div>;
  }

  return (
    <div className="user-details-page">
      <div className="header">
        <button className="back-button" onClick={handleBackClick}>← Back to Dashboard</button>
        <h2>User Details</h2>
      </div>

      {message && (
        <p className={message.includes('success') ? 'success-message' : 'error-message'}>
          {message}
        </p>
      )}

      <div className="content">
        <div className="user-info-card">
          <h3>Basic Information</h3>
          <div className="info-grid">
            <div className="info-item">
              <label>Name:</label>
              <span>{userDetails.name}</span>
            </div>
            <div className="info-item">
              <label>Phone:</label>
              <span>{userDetails.phone}</span>
            </div>
            <div className="info-item">
              <label>Role:</label>
              <span>{userDetails.role}</span>
            </div>
            <div className="info-item">
              <label>UUID:</label>
              <span className="uuid">{userId}</span>
            </div>
          </div>
        </div>

        <div className="assign-projects-section">
          <h3>Assign New Projects</h3>
          <div className="assign-form">
            <select 
              multiple
              value={selectedProjects}
              onChange={handleProjectChange}
              className="project-select"
              disabled={loading}
            >
              {allProjects
                .filter(project => !userDetails.projects.some(p => p.uuid === project.uuid))
                .map(project => (
                  <option key={project.uuid} value={project.uuid}>
                    {project.name} - {project.description || 'No Description'}
                  </option>
                ))
              }
            </select>
            <small>Hold Ctrl/Cmd to select multiple projects</small>
            <button 
              className="assign-button"
              onClick={handleAssignProjects} 
              disabled={selectedProjects.length === 0 || loading}
            >
              {loading ? 'Assigning...' : 'Assign Selected Projects'}
            </button>
          </div>
        </div>

        <div className="assign-items-section">
          <h3>Assign Items to Project</h3>
          <div className="assign-form">
            <div className="form-group">
              <label>Select Project:</label>
              <select 
                value={selectedProjectForItems}
                onChange={(e) => setSelectedProjectForItems(e.target.value)}
                className="project-select-single"
                disabled={loading}
              >
                <option value="">Select a project</option>
                {userDetails.projects.map(project => (
                  <option key={project.uuid} value={project.uuid}>
                    {project.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Select Items:</label>
              <select 
                multiple
                value={selectedItems}
                onChange={handleItemChange}
                className="items-select"
                disabled={loading || !selectedProjectForItems}
              >
                {allItems
                  .filter(item => !userDetails.projects
                    .find(p => p.uuid === selectedProjectForItems)?.items
                    .some(i => i.uuid === item.uuid))
                  .map(item => (
                    <option key={item.uuid} value={item.uuid}>
                      {item.name} - {item.category || 'No Category'}
                    </option>
                  ))
                }
              </select>
              <small>Hold Ctrl/Cmd to select multiple items</small>
            </div>

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
                className="assign-button"
                onClick={handleAssignItems} 
                disabled={!selectedProjectForItems || selectedItems.length === 0 || loading}
              >
                {loading ? 'Assigning...' : 'Assign Items to Project'}
              </button>
              <button 
                className="create-new-btn"
                onClick={() => setShowCreateItem(true)}
              >
                Create New Item
              </button>
            </div>
          </div>
        </div>

        <div className="projects-section">
          <h3>Assigned Projects ({userDetails.projects.length})</h3>
          <div className="projects-grid">
            {userDetails.projects.map((project) => (
              <div key={project.uuid} className="project-card">
                <div className="project-header">
                  <h4>{project.name}</h4>
                  <span className="location">{project.location}</span>
                </div>
                <p className="description">{project.description || 'No description'}</p>
                <div className="balances-section">
                  <div className="balance-row">
                    <span className="balance-label">PO Balance:</span>
                    <span className="balance-value">{project.po_balance || 0}</span>
                  </div>
                  <div className="balance-row">
                    <span className="balance-label">Estimated Balance:</span>
                    <span className="balance-value">{project.estimated_balance || 0}</span>
                  </div>
                  <div className="balance-row">
                    <span className="balance-label">Actual Balance:</span>
                    <span className="balance-value">{project.actual_balance || 0}</span>
                  </div>
                </div>
                <div className="items-section">
                  <h5>Project Items ({project.items.length})</h5>
                  {project.items.length > 0 ? (
                    <ul className="items-list">
                      {project.items.map((item) => (
                        <li key={item.uuid}>
                          {item.name} {item.category && `- ${item.category}`}
                          <span className="item-balance"> (Balance: {item.item_balance || 0})</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="no-items">No items assigned to this project</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

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

export default UserDetails;