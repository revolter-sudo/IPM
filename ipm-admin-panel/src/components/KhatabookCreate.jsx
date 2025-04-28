import React, { useState, useEffect } from 'react';
import axios from 'axios';
import '../styles/KhatabookCreate.css';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

const KhatabookCreate = ({ token, onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    amount: '',
    remarks: '',
    person_id: '',
    project_id: '',
    expense_date: new Date().toISOString().slice(0, 16),
    payment_mode: '',
    item_ids: []
  });

  const [newPerson, setNewPerson] = useState({
    name: '',
    phone_number: '',
    account_number: '',
    ifsc_code: '',
    upi_number: ''
  });

  const [isCreatingPerson, setIsCreatingPerson] = useState(false);
  const [files, setFiles] = useState([]);
  const [persons, setPersons] = useState([]);
  const [projects, setProjects] = useState([]);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [personError, setPersonError] = useState('');

  useEffect(() => {
    fetchPersons();
    fetchProjects();
    fetchItems();
  }, []);

  const fetchPersons = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/payments/persons`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      setPersons(response.data.data || []);
    } catch (err) {
      setError('Failed to fetch persons');
    }
  };

  const fetchProjects = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/projects`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      setProjects(response.data.data || []);
    } catch (err) {
      setError('Failed to fetch projects');
    }
  };

  const fetchItems = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/payments/items`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      setItems(response.data.data || []);
    } catch (err) {
      setError('Failed to fetch items');
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    if (name === 'expense_date') {
      const date = new Date(value);
      setFormData(prev => ({
        ...prev,
        [name]: date.toISOString()
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        [name]: value
      }));
    }
  };

  const handleItemChange = (e) => {
    const selectedOptions = Array.from(e.target.selectedOptions, option => option.value);
    setFormData(prev => ({
      ...prev,
      item_ids: selectedOptions
    }));
  };

  const handleFileChange = (e) => {
    setFiles(Array.from(e.target.files));
  };

  const handleNewPersonChange = (e) => {
    const { name, value } = e.target;
    setNewPerson(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const validatePerson = () => {
    if (!newPerson.name) {
      setPersonError('Name is required');
      return false;
    }
    if (!newPerson.phone_number) {
      setPersonError('Phone number is required');
      return false;
    }
    if (!/^\d{10}$/.test(newPerson.phone_number)) {
      setPersonError('Phone number must be 10 digits');
      return false;
    }
    if (newPerson.account_number && !/^\d{11,16}$/.test(newPerson.account_number)) {
      setPersonError('Account number must be between 11 and 16 digits');
      return false;
    }
    if (newPerson.ifsc_code && !/^[A-Z]{4}0[A-Z0-9]{6}$/.test(newPerson.ifsc_code)) {
      setPersonError('Invalid IFSC code format');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      let finalFormData = { ...formData };

      if (isCreatingPerson) {
        if (!validatePerson()) {
          setLoading(false);
          return;
        }

        const personResponse = await axios.post(
          `${API_BASE_URL}/payments/persons`,
          newPerson,
          {
            headers: { 'Authorization': `Bearer ${token}` }
          }
        );

        finalFormData.person_id = personResponse.data.data.uuid;
      }

      const formDataObj = new FormData();
      Object.keys(finalFormData).forEach(key => {
        if (key === 'item_ids') {
          finalFormData[key].forEach(itemId => {
            formDataObj.append('item_ids[]', itemId);
          });
        } else {
          formDataObj.append(key, finalFormData[key]);
        }
      });

      files.forEach(file => {
        formDataObj.append('files[]', file);
      });

      await axios.post(
        `${API_BASE_URL}/khatabook/entries`,
        formDataObj,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );

      onSuccess();
      onClose();
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to create khatabook entry');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="khatabook-create">
      <h2>Create Khatabook Entry</h2>
      {error && <p className="error-message">{error}</p>}
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="amount">Amount *</label>
          <input
            type="number"
            id="amount"
            name="amount"
            value={formData.amount}
            onChange={handleChange}
            required
            disabled={loading}
            step="0.01"
            min="0"
          />
        </div>

        <div className="form-group">
          <label htmlFor="project_id">Project *</label>
          <select
            id="project_id"
            name="project_id"
            value={formData.project_id}
            onChange={handleChange}
            required
            disabled={loading}
          >
            <option value="">Select Project</option>
            {projects.map(project => (
              <option key={project.uuid} value={project.uuid}>
                {project.name}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="person_id">Person *</label>
          {!isCreatingPerson ? (
            <>
              <div className="select-with-button">
                <select
                  id="person_id"
                  name="person_id"
                  value={formData.person_id}
                  onChange={handleChange}
                  required={!isCreatingPerson}
                  disabled={loading}
                >
                  <option value="">Select Person</option>
                  {persons.map(person => (
                    <option key={person.uuid} value={person.uuid}>
                      {person.name} ({person.phone_number})
                    </option>
                  ))}
                </select>
                <button 
                  type="button" 
                  onClick={() => setIsCreatingPerson(true)}
                  className="new-person-btn"
                >
                  + New Person
                </button>
              </div>
            </>
          ) : (
            <div className="new-person-form">
              {personError && <p className="error-message">{personError}</p>}
              <div className="form-row">
                <input
                  type="text"
                  name="name"
                  value={newPerson.name}
                  onChange={handleNewPersonChange}
                  placeholder="Name *"
                  disabled={loading}
                />
                <input
                  type="text"
                  name="phone_number"
                  value={newPerson.phone_number}
                  onChange={handleNewPersonChange}
                  placeholder="Phone Number *"
                  disabled={loading}
                />
              </div>
              <div className="form-row">
                <input
                  type="text"
                  name="account_number"
                  value={newPerson.account_number}
                  onChange={handleNewPersonChange}
                  placeholder="Account Number"
                  disabled={loading}
                />
                <input
                  type="text"
                  name="ifsc_code"
                  value={newPerson.ifsc_code}
                  onChange={handleNewPersonChange}
                  placeholder="IFSC Code"
                  disabled={loading}
                />
              </div>
              <div className="form-row">
                <input
                  type="text"
                  name="upi_number"
                  value={newPerson.upi_number}
                  onChange={handleNewPersonChange}
                  placeholder="UPI Number"
                  disabled={loading}
                />
                <button
                  type="button"
                  onClick={() => {
                    setIsCreatingPerson(false);
                    setPersonError('');
                  }}
                  disabled={loading}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="item_ids">Items</label>
          <select
            id="item_ids"
            name="item_ids"
            multiple
            value={formData.item_ids}
            onChange={handleItemChange}
            disabled={loading}
          >
            {items.map(item => (
              <option key={item.uuid} value={item.uuid}>
                {item.name} {item.category ? `- ${item.category}` : ''}
              </option>
            ))}
          </select>
          <small>Hold Ctrl/Cmd to select multiple items</small>
        </div>

        <div className="form-group">
          <label htmlFor="expense_date">Expense Date</label>
          <input
            type="datetime-local"
            id="expense_date"
            name="expense_date"
            value={formData.expense_date ? formData.expense_date.slice(0, 16) : ''}
            onChange={handleChange}
            required
            disabled={loading}
          />
        </div>

        <div className="form-group">
          <label htmlFor="payment_mode">Payment Mode</label>
          <select
            id="payment_mode"
            name="payment_mode"
            value={formData.payment_mode}
            onChange={handleChange}
            disabled={loading}
          >
            <option value="">Select Payment Mode</option>
            <option value="cash">Cash</option>
            <option value="upi">UPI</option>
            <option value="bank_transfer">Bank Transfer</option>
            <option value="cheque">Cheque</option>
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="remarks">Remarks</label>
          <textarea
            id="remarks"
            name="remarks"
            value={formData.remarks}
            onChange={handleChange}
            disabled={loading}
          />
        </div>

        <div className="form-group">
          <label htmlFor="files">Attachments</label>
          <input
            type="file"
            id="files"
            multiple
            onChange={handleFileChange}
            disabled={loading}
          />
        </div>

        <div className="button-group">
          <button type="submit" disabled={loading}>
            {loading ? 'Creating...' : 'Create Entry'}
          </button>
          <button type="button" onClick={onClose} disabled={loading}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};

export default KhatabookCreate;