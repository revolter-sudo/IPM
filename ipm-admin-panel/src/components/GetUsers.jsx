import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getAllUsers } from '../services/api';
import '../styles/GetUsers.css';

const GetUsers = ({ token }) => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const response = await getAllUsers(token);
        setUsers(response.data || []);
      } catch (err) {
        setError(err.message || 'Failed to fetch users');
      } finally {
        setLoading(false);
      }
    };
    fetchUsers();
  }, [token]);

  const handleUserClick = (userId) => {
    navigate(`/user-details/${userId}`);
  };

  const filteredUsers = users.filter(user =>
    user.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    user.role.toLowerCase().includes(searchQuery.toLowerCase()) ||
    user.phone.includes(searchQuery)
  );

  if (loading) {
    return <div className="loading">Loading users...</div>;
  }

  if (error) {
    return <div className="error">Error: {error}</div>;
  }

  return (
    <>
      <div className="users-search">
        <input
          type="text"
          placeholder="Search users by name, role, or phone..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="search-input"
        />
      </div>
      <div className="users-list">
        {filteredUsers.map((user) => (
          <div 
            key={user.uuid} 
            className="user-card"
            onClick={() => handleUserClick(user.uuid)}
          >
            <div className="user-info">
              <div className="user-name">{user.name}</div>
              <div className="user-role">{user.role}</div>
              <div className="user-phone">{user.phone}</div>
              {user.email && <div className="user-email">{user.email}</div>}
            </div>
          </div>
        ))}
        {filteredUsers.length === 0 && searchQuery && (
          <div className="no-results">
            No users found matching "{searchQuery}"
          </div>
        )}
      </div>
    </>
  );
};

export default GetUsers;
