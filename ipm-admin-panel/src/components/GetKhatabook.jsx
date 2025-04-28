import React, { useState, useEffect } from 'react';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { getKhatabookEntries, getAllUsers, getAllProjects, getAllItems } from '../services/api';
import '../styles/Khatabook.css';

const GetKhatabook = ({ token }) => {
  const [entries, setEntries] = useState([]);
  const [totalAmount, setTotalAmount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [users, setUsers] = useState([]);
  const [projects, setProjects] = useState([]);
  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [totalPages, setTotalPages] = useState(0);
  const [totalEntries, setTotalEntries] = useState(0);

  const [filters, setFilters] = useState({
    user_id: '',
    item_id: '',
    project_id: '',
    min_amount: '',
    max_amount: '',
    start_date: null,
    end_date: null,
    payment_mode: ''
  });

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const [usersResponse, projectsResponse, itemsResponse] = await Promise.all([
          getAllUsers(token),
          getAllProjects(token),
          getAllItems(token)
        ]);
        setUsers(usersResponse.data);
        setProjects(projectsResponse.data);
        setItems(itemsResponse.data);
      } catch (error) {
        setError('Failed to fetch initial data');
      }
    };

    fetchInitialData();
    fetchKhatabookEntries();
  }, [token]);

  const fetchKhatabookEntries = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getKhatabookEntries({ ...filters, page, page_size: pageSize }, token);
      setEntries(response.data.entries);
      setTotalAmount(response.data.total_amount);
      setTotalPages(response.data.total_pages);
      setTotalEntries(response.data.entries_count);
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (field) => (event) => {
    setFilters(prev => ({
      ...prev,
      [field]: event.target.value
    }));
  };

  const handleDateChange = (field) => (date) => {
    setFilters(prev => ({
      ...prev,
      [field]: date
    }));
  };

  const handleApplyFilters = () => {
    setPage(1);
    fetchKhatabookEntries();
  };

  const handleResetFilters = () => {
    setFilters({
      user_id: '',
      item_id: '',
      project_id: '',
      min_amount: '',
      max_amount: '',
      start_date: null,
      end_date: null,
      payment_mode: ''
    });
    setPage(1);
  };

  const handlePageChange = (event, newPage) => {
    setPage(newPage);
    fetchKhatabookEntries();
  };

  const handleChangeRowsPerPage = (event) => {
    setPageSize(parseInt(event.target.value, 10));
    setPage(1);
    fetchKhatabookEntries();
  };

  return (
    <div className="khatabook-view">
      <div className="khatabook-header">
        <h4>Khatabook Entries</h4>
      </div>

      <div className="filter-section">
        <div className="filter-grid">
          <div className="filter-item">
            <label>User</label>
            <select
              value={filters.user_id}
              onChange={(e) => handleFilterChange('user_id')(e)}
            >
              <option value="">All Users</option>
              {users.map((user) => (
                <option key={user.uuid} value={user.uuid}>
                  {user.name}
                </option>
              ))}
            </select>
          </div>

          <div className="filter-item">
            <label>Project</label>
            <select
              value={filters.project_id}
              onChange={(e) => handleFilterChange('project_id')(e)}
            >
              <option value="">All Projects</option>
              {projects.map((project) => (
                <option key={project.uuid} value={project.uuid}>
                  {project.name}
                </option>
              ))}
            </select>
          </div>

          <div className="filter-item">
            <label>Item</label>
            <select
              value={filters.item_id}
              onChange={(e) => handleFilterChange('item_id')(e)}
            >
              <option value="">All Items</option>
              {items.map((item) => (
                <option key={item.uuid} value={item.uuid}>
                  {item.name}
                </option>
              ))}
            </select>
          </div>

          <div className="filter-item">
            <label>Payment Mode</label>
            <select
              value={filters.payment_mode}
              onChange={(e) => handleFilterChange('payment_mode')(e)}
            >
              <option value="">All Modes</option>
              <option value="cash">Cash</option>
              <option value="upi">UPI</option>
              <option value="bank_transfer">Bank Transfer</option>
              <option value="cheque">Cheque</option>
            </select>
          </div>

          <div className="filter-item">
            <label>Min Amount</label>
            <input
              type="number"
              value={filters.min_amount}
              onChange={(e) => handleFilterChange('min_amount')(e)}
              placeholder="Enter min amount"
            />
          </div>

          <div className="filter-item">
            <label>Max Amount</label>
            <input
              type="number"
              value={filters.max_amount}
              onChange={(e) => handleFilterChange('max_amount')(e)}
              placeholder="Enter max amount"
            />
          </div>

          <div className="filter-item">
            <label>Start Date</label>
            <LocalizationProvider dateAdapter={AdapterDateFns}>
              <DatePicker
                value={filters.start_date}
                onChange={handleDateChange('start_date')}
                renderInput={(params) => <input {...params} />}
              />
            </LocalizationProvider>
          </div>

          <div className="filter-item">
            <label>End Date</label>
            <LocalizationProvider dateAdapter={AdapterDateFns}>
              <DatePicker
                value={filters.end_date}
                onChange={handleDateChange('end_date')}
                renderInput={(params) => <input {...params} />}
              />
            </LocalizationProvider>
          </div>
        </div>

        <div className="filter-actions">
          <button className="filter-button apply-filter" onClick={handleApplyFilters}>
            Apply Filters
          </button>
          <button className="filter-button reset-filter" onClick={handleResetFilters}>
            Reset Filters
          </button>
        </div>
      </div>

      <div className="summary-section">
        <div className="total-amount">
          Total Amount: <span>₹{totalAmount.toFixed(2)}</span>
        </div>
        <div className="total-entries">
          Total Entries: {totalEntries}
        </div>
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {loading ? (
        <div className="loading-container">
          <div className="loading-spinner"></div>
        </div>
      ) : (
        <div className="table-container">
          <table className="khatabook-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Amount</th>
                <th>User</th>
                <th>Project</th>
                <th>Person</th>
                <th>Items</th>
                <th>Payment Mode</th>
                <th>Balance After Entry</th>
                <th>Remarks</th>
              </tr>
            </thead>
            <tbody>
              {entries.length === 0 ? (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center' }}>No entries found</td>
                </tr>
              ) : (
                entries.map((entry) => (
                  <tr key={entry.uuid}>
                    <td className="date-cell">
                      {entry.expense_date 
                        ? new Date(entry.expense_date).toLocaleString('en-IN', {
                            weekday: 'short',
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                            hour12: true
                          })
                        : 'N/A'
                      }
                    </td>
                    <td className="amount-cell">₹{entry.amount.toFixed(2)}</td>
                    <td>{entry.user?.name || 'N/A'}</td>
                    <td>{entry.project?.name || 'N/A'}</td>
                    <td>{entry.person?.name || 'N/A'}</td>
                    <td>{entry.items?.map(item => item.name).join(', ') || 'N/A'}</td>
                    <td>
                      <span className={`payment-mode ${entry.payment_mode}`}>
                        {entry.payment_mode?.replace('_', ' ') || 'N/A'}
                      </span>
                    </td>
                    <td className="amount-cell">₹{entry.balance_after_entry?.toFixed(2) || 'N/A'}</td>
                    <td>{entry.remarks || 'N/A'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>

          {entries.length > 0 && (
            <div className="pagination-container">
              <div className="rows-per-page">
                <span>Rows per page:</span>
                <select
                  value={pageSize}
                  onChange={handleChangeRowsPerPage}
                >
                  <option value={10}>10</option>
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                </select>
              </div>

              <div className="pagination-controls">
                <button
                  className="page-button"
                  onClick={() => handlePageChange(null, page - 1)}
                  disabled={page === 1}
                >
                  Previous
                </button>
                <span>Page {page} of {totalPages}</span>
                <button
                  className="page-button"
                  onClick={() => handlePageChange(null, page + 1)}
                  disabled={page === totalPages}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default GetKhatabook;