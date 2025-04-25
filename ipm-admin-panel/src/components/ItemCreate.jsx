import React, { useState } from "react";
import axios from "axios";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

const ItemCreate = ({ token, onClose, onItemCreated }) => {
  const [name, setName] = useState("");
  const [hasAdditionalInfo, setHasAdditionalInfo] = useState(false);
  const [category, setCategory] = useState("");
  const [listTag, setListTag] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      // Build URL with query parameters, converting boolean to 1/0
      let url = `${API_BASE_URL}/payments/items?name=${encodeURIComponent(name)}&has_additional_info=${hasAdditionalInfo ? 1 : 0}`;
      
      if (category) {
        url += `&category=${encodeURIComponent(category)}`;
      }
      if (listTag) {
        url += `&list_tag=${encodeURIComponent(listTag)}`;
      }

      // Debug logging
      console.log('Request URL:', url);

      const response = await axios({
        method: 'post',
        url,
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      console.log('Response:', response.data);

      if (response.status === 201) {
        if (onItemCreated) {
          onItemCreated(response.data.data);
        }
        onClose();
      }
    } catch (err) {
      console.error('Full error:', err);
      console.error('Error details:', {
        status: err.response?.status,
        statusText: err.response?.statusText,
        data: err.response?.data,
        validationErrors: err.response?.data?.detail
      });
      
      // Show validation error details to the user
      const errorMessage = err.response?.data?.detail?.[0]?.msg 
        || err.response?.data?.detail 
        || err.response?.data?.message 
        || err.message 
        || "Failed to create item";
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="item-create">
      <h2>Create New Item</h2>
      <form onSubmit={handleSubmit} className="item-create-form">
        <div className="form-group">
          <label htmlFor="name">Item Name *</label>
          <input
            id="name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            disabled={loading}
          />
        </div>
        <div className="form-group">
          <label htmlFor="hasAdditionalInfo">Has Additional Info</label>
          <select
            id="hasAdditionalInfo"
            value={String(hasAdditionalInfo)}
            onChange={(e) => setHasAdditionalInfo(e.target.value === "true")}
            disabled={loading}
          >
            <option value="false">No</option>
            <option value="true">Yes</option>
          </select>
        </div>
        <div className="form-group">
          <label htmlFor="category">Category (optional)</label>
          <input
            id="category"
            type="text"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            disabled={loading}
          />
        </div>
        <div className="form-group">
          <label htmlFor="listTag">List Tag (optional)</label>
          <select
            id="listTag"
            value={listTag}
            onChange={(e) => setListTag(e.target.value)}
            disabled={loading}
          >
            <option value="">None</option>
            <option value="khatabook">khatabook</option>
            <option value="payment">payment</option>
          </select>
        </div>
        {error && <p className="error" style={{ color: 'red', marginTop: '10px' }}>{error}</p>}
        <div className="button-group" style={{ marginTop: '20px' }}>
          <button type="submit" disabled={loading}>
            {loading ? "Creating..." : "Create Item"}
          </button>
          <button type="button" onClick={onClose} disabled={loading}>
            Cancel
          </button>
        </div>
      </form>
      <style jsx>{`
        .item-create-form {
          display: flex;
          flex-direction: column;
          gap: 15px;
        }
        .form-group {
          display: flex;
          flex-direction: column;
          gap: 5px;
        }
        .form-group label {
          font-weight: 500;
        }
        .form-group input,
        .form-group select {
          padding: 8px;
          border: 1px solid #ccc;
          border-radius: 4px;
        }
        .button-group {
          display: flex;
          gap: 10px;
        }
        .button-group button {
          padding: 8px 16px;
          border-radius: 4px;
          border: none;
          cursor: pointer;
        }
        .button-group button[type="submit"] {
          background-color: #0066cc;
          color: white;
        }
        .button-group button[type="button"] {
          background-color: #e0e0e0;
        }
        .button-group button:disabled {
          opacity: 0.7;
          cursor: not-allowed;
        }
      `}</style>
    </div>
  );
};

export default ItemCreate;
