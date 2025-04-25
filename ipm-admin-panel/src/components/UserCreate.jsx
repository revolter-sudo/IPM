import React, { useState } from 'react';
import { createUser } from '../services/api';

const UserCreate = ({ token, onSuccess }) => {
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    password: '',
    role: 'SubContractor',
    person: {
      name: '',
      phone_number: '',
      account_number: '',
      account_number_confirmation: '',
      ifsc_code: '',
    },
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [accountNumberError, setAccountNumberError] = useState('');

  const roles = [
    'SubContractor',
    'SiteEngineer',
    'ProjectManager',
    'Admin',
    'Accountant',
    'Inspector',
    'RecordLivePayment',
    'SuperAdmin'
  ];

  const validateAccountNumber = (accountNumber) => {
    // Remove any spaces or special characters
    const cleanNumber = accountNumber.replace(/\s|-/g, '');
    
    // Check if it contains only numbers
    if (!/^\d+$/.test(cleanNumber)) {
      return 'Account number should contain only numbers';
    }
    
    // Check length (most Indian bank accounts are between 11 to 16 digits)
    if (cleanNumber.length < 11 || cleanNumber.length > 16) {
      return 'Account number should be between 11 and 16 digits';
    }
    
    return '';
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    
    if (name.startsWith('person.')) {
      const personField = name.split('.')[1];
      setFormData(prev => {
        const updatedData = {
          ...prev,
          person: {
            ...prev.person,
            [personField]: value,
          }
        };

        // Clear any existing error when either account number field changes
        if (personField === 'account_number' || personField === 'account_number_confirmation') {
          setAccountNumberError('');
          
          // Validate matching numbers if both fields have values
          const mainAccount = personField === 'account_number' ? value : updatedData.person.account_number;
          const confirmAccount = personField === 'account_number_confirmation' ? value : updatedData.person.account_number_confirmation;
          
          if (mainAccount && confirmAccount && mainAccount !== confirmAccount) {
            setAccountNumberError('Account numbers do not match');
          } else if (mainAccount) {
            const validationError = validateAccountNumber(mainAccount);
            if (validationError) setAccountNumberError(validationError);
          }
        }

        return updatedData;
      });
    } else {
      setFormData(prev => ({
        ...prev,
        [name]: value,
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validate account numbers match and are valid
    if (formData.person.account_number) {
      const validationError = validateAccountNumber(formData.person.account_number);
      if (validationError) {
        setAccountNumberError(validationError);
        return;
      }
      
      if (formData.person.account_number !== formData.person.account_number_confirmation) {
        setAccountNumberError('Account numbers do not match');
        return;
      }
    }
    
    setLoading(true);
    setError('');
    setSuccessMessage('');
    try {
      // Prepare data to send (exclude confirmation field)
      const userData = {
        name: formData.name,
        phone: formData.phone,
        password: formData.password,
        role: formData.role,
        person: {
          name: formData.person.name,
          phone_number: formData.person.phone_number,
          account_number: formData.person.account_number.replace(/\s|-/g, ''),
          ifsc_code: formData.person.ifsc_code,
        },
      };
      await createUser(userData, token);
      setSuccessMessage('User created successfully.');
      setFormData({
        name: '',
        phone: '',
        password: '',
        role: 'SubContractor',
        person: {
          name: '',
          phone_number: '',
          account_number: '',
          account_number_confirmation: '',
          ifsc_code: '',
        },
      });
      setAccountNumberError('');
      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      setError(err.message || 'Failed to create user.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>Create User</h2>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {successMessage && <p style={{ color: 'green' }}>{successMessage}</p>}
      <form onSubmit={handleSubmit}>
        <div>
          <label>Name:</label><br />
          <input
            type="text"
            name="name"
            value={formData.name}
            onChange={handleChange}
            required
          />
        </div>
        <div>
          <label>Phone:</label><br />
          <input
            type="text"
            name="phone"
            value={formData.phone}
            onChange={handleChange}
            required
          />
        </div>
        <div>
          <label>Password:</label><br />
          <input
            type="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            required
          />
        </div>
        <div>
          <label>Role:</label><br />
          <select 
            name="role" 
            value={formData.role} 
            onChange={handleChange}
            style={{ padding: '8px', width: '100%', maxWidth: '300px' }}
          >
            {roles.map((role) => (
              <option key={role} value={role}>{role}</option>
            ))}
          </select>
        </div>
        <fieldset>
          <legend>Person Details</legend>
          <div>
            <label>Person Name:</label><br />
            <input
              type="text"
              name="person.name"
              value={formData.person.name}
              onChange={handleChange}
            />
          </div>
          <div>
            <label>Phone Number:</label><br />
            <input
              type="text"
              name="person.phone_number"
              value={formData.person.phone_number}
              onChange={handleChange}
            />
          </div>
          <div>
            <label>Account Number:</label><br />
            <input
              type="text"
              name="person.account_number"
              value={formData.person.account_number}
              onChange={handleChange}
              placeholder="Enter 11-16 digit account number"
            />
          </div>
          <div>
            <label>Confirm Account Number:</label><br />
            <input
              type="text"
              name="person.account_number_confirmation"
              value={formData.person.account_number_confirmation}
              onChange={handleChange}
              placeholder="Re-enter account number"
            />
            {accountNumberError && (
              <p style={{ color: 'red', fontSize: '0.8em', margin: '4px 0' }}>
                {accountNumberError}
              </p>
            )}
          </div>
          <div>
            <label>IFSC Code:</label><br />
            <input
              type="text"
              name="person.ifsc_code"
              value={formData.person.ifsc_code}
              onChange={handleChange}
            />
          </div>
        </fieldset>
        <button type="submit" disabled={loading || accountNumberError}>
          {loading ? 'Creating...' : 'Create User'}
        </button>
      </form>
    </div>
  );
};

export default UserCreate;
