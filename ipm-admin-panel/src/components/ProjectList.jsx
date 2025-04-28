import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getAllProjects } from '../services/api';
import '../styles/ProjectList.css';

const ProjectList = ({ token }) => {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const data = await getAllProjects(token);
        setProjects(data.data || []);
      } catch (err) {
        setError(err.message || 'Failed to fetch projects');
      } finally {
        setLoading(false);
      }
    };

    fetchProjects();
  }, [token]);

  const handleProjectClick = (projectId) => {
    navigate(`/project-details/${projectId}`);
  };

  const filteredProjects = projects.filter(project =>
    project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (project.description && project.description.toLowerCase().includes(searchQuery.toLowerCase())) ||
    (project.location && project.location.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  if (loading) {
    return <div className="loading">Loading projects...</div>;
  }

  if (error) {
    return <div className="error">Error: {error}</div>;
  }

  return (
    <>
      <div className="projects-search">
        <input
          type="text"
          placeholder="Search projects by name, description, or location..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="search-input"
        />
      </div>
      <div className="projects-list">
        {filteredProjects.map((project) => (
          <div 
            key={project.uuid} 
            className="project-card"
            onClick={() => handleProjectClick(project.uuid)}
          >
            <div className="project-info">
              <div className="project-name">{project.name}</div>
              <div className="project-description">{project.description || 'No description available'}</div>
              {project.location && (
                <div className="project-location">
                  📍 {project.location}
                </div>
              )}
              <div className="project-balances">
                <div className="balance-item">
                  <span className="balance-label">PO Balance</span>
                  <span className="balance-value">{project.po_balance || 0}</span>
                </div>
                <div className="balance-item">
                  <span className="balance-label">Est Balance</span>
                  <span className="balance-value">{project.estimated_balance || 0}</span>
                </div>
                <div className="balance-item">
                  <span className="balance-label">Actual Balance</span>
                  <span className="balance-value">{project.actual_balance || 0}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
        {filteredProjects.length === 0 && searchQuery && (
          <div className="no-results">
            No projects found matching "{searchQuery}"
          </div>
        )}
      </div>
    </>
  );
};

export default ProjectList;
