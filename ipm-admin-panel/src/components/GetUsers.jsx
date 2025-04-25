import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getAllUsers } from '../services/api';

const GetUsers = ({ token }) => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
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

  if (loading) {
    return <div className="loading">Loading users...</div>;
  }

  if (error) {
    return <div className="error">Error: {error}</div>;
  }

  return (
    <div className="users-list">
      {users.map((user) => (
        <div 
          key={user.uuid} 
          className="user-card"
          onClick={() => handleUserClick(user.uuid)}
        >
          <div className="user-info">
            <div className="user-name">{user.name}</div>
            <div className="user-role">{user.role}</div>
            <div className="user-phone">{user.phone}</div>
          </div>
          <div className="user-uuid">
            {user.uuid}
          </div>
        </div>
      ))}

      <style jsx>{`
        .users-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
          padding: 20px;
        }

        .user-card {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px;
          background: #f8f9fa;
          border-radius: 6px;
          transition: all 0.2s;
          cursor: pointer;
        }

        .user-card:hover {
          background: #f1f3f5;
          transform: translateY(-2px);
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .user-info {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .user-name {
          font-weight: 500;
          color: #212529;
        }

        .user-role {
          font-size: 0.875rem;
          color: #6c757d;
        }

        .user-phone {
          font-size: 0.875rem;
          color: #495057;
        }

        .user-uuid {
          font-family: monospace;
          font-size: 0.875rem;
          color: #495057;
          background: #e9ecef;
          padding: 4px 8px;
          border-radius: 4px;
          min-width: 120px;
          text-align: right;
        }

        .loading {
          text-align: center;
          padding: 20px;
          color: #6c757d;
        }

        .error {
          color: #dc3545;
          padding: 20px;
          text-align: center;
        }
      `}</style>
    </div>
  );
};

export default GetUsers;
