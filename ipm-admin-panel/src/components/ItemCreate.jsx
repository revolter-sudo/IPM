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
      let url = `${API_BASE_URL}/payments/items?name=${encodeURIComponent(name)}&has_additional_info=${hasAdditionalInfo ? 1 : 0}`;
      
      if (category) {
        url += `&category=${encodeURIComponent(category)}`;
      }
      if (listTag) {
        url += `&list_tag=${encodeURIComponent(listTag)}`;
      }

      await axios.post(url, null, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      onItemCreated && onItemCreated();
      onClose && onClose();
    } catch (err) {
      const errorMessage = err.response?.data?.message || err.message || 'Failed to create item';
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
        {error && <p className="error">{error}</p>}
        <div className="button-group">
          <button type="submit" disabled={loading}>
            {loading ? "Creating..." : "Create Item"}
          </button>
          <button type="button" onClick={onClose} disabled={loading}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};

export default ItemCreate;
