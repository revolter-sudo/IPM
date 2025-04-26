import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getUserDetails, assignUserToProject, assignItemToProject, getAllProjects, getAllItems } from '../services/api';
import ItemCreate from './ItemCreate';

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

      <style jsx>{`
        .user-details-page {
          padding: 24px;
          max-width: 1200px;
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
          background: #f8f9fa;
          border-radius: 4px;
          cursor: pointer;
          font-weight: 500;
        }

        .back-button:hover {
          background: #e9ecef;
        }

        .content {
          display: flex;
          flex-direction: column;
          gap: 24px;
        }

        .user-info-card {
          background: white;
          border-radius: 8px;
          padding: 20px;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .info-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 16px;
          margin-top: 16px;
        }

        .info-item {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .info-item label {
          font-weight: 500;
          color: #6c757d;
        }

        .uuid {
          font-family: monospace;
          background: #f8f9fa;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 0.9em;
        }

        .assign-projects-section {
          background: white;
          border-radius: 8px;
          padding: 20px;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .assign-form {
          display: flex;
          flex-direction: column;
          gap: 12px;
          margin-top: 16px;
        }

        .project-select {
          width: 100%;
          min-height: 200px;
          padding: 8px;
          border: 1px solid #dee2e6;
          border-radius: 4px;
        }

        .assign-button {
          padding: 10px 20px;
          background: #0066cc;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: 500;
          margin-top: 8px;
        }

        .assign-button:disabled {
          background: #cccccc;
          cursor: not-allowed;
        }

        .projects-section {
          background: white;
          border-radius: 8px;
          padding: 20px;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .projects-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 20px;
          margin-top: 16px;
        }

        .project-card {
          background: #f8f9fa;
          border-radius: 6px;
          padding: 16px;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .project-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
        }

        .project-header h4 {
          margin: 0;
          color: #212529;
        }

        .location {
          font-size: 0.9em;
          color: #6c757d;
        }

        .description {
          color: #495057;
          font-size: 0.9em;
          margin: 0;
        }

        .items-section {
          border-top: 1px solid #dee2e6;
          padding-top: 12px;
        }

        .items-section h5 {
          margin: 0 0 8px 0;
          color: #495057;
        }

        .items-list {
          list-style: none;
          padding: 0;
          margin: 0;
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .items-list li {
          font-size: 0.9em;
          color: #6c757d;
        }

        .item-balance {
          font-size: 0.9em;
          color: #495057;
        }

        .no-items {
          color: #6c757d;
          font-size: 0.9em;
          margin: 0;
        }

        .success-message {
          color: #198754;
          padding: 12px;
          background: #d1e7dd;
          border-radius: 4px;
          margin: 16px 0;
        }

        .error-message {
          color: #dc3545;
          padding: 12px;
          background: #f8d7da;
          border-radius: 4px;
          margin: 16px 0;
        }

        .loading {
          text-align: center;
          padding: 40px;
          color: #6c757d;
        }

        .assign-items-section {
          background: white;
          border-radius: 8px;
          padding: 20px;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .form-group {
          margin-bottom: 16px;
        }

        .form-group label {
          display: block;
          margin-bottom: 8px;
          font-weight: 500;
          color: #495057;
        }

        .project-select-single {
          width: 100%;
          padding: 8px;
          border: 1px solid #dee2e6;
          border-radius: 4px;
          margin-bottom: 16px;
        }

        .items-select {
          width: 100%;
          min-height: 200px;
          padding: 8px;
          border: 1px solid #dee2e6;
          border-radius: 4px;
        }

        .selected-items-balances {
          margin-top: 16px;
          padding: 16px;
          border: 1px solid #dee2e6;
          border-radius: 4px;
        }

        .balance-input-row {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 8px;
        }

        .balance-input-row label {
          min-width: 150px;
        }

        .balance-input-row input {
          width: 120px;
          padding: 6px;
          border: 1px solid #dee2e6;
          border-radius: 4px;
        }

        .button-group {
          display: flex;
          gap: 12px;
          margin-top: 16px;
        }

        .create-new-btn {
          padding: 10px 20px;
          background: #28a745;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: 500;
        }

        .create-new-btn:hover {
          background: #218838;
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
      `}</style>
    </div>
  );
};

export default UserDetails;