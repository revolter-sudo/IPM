import React, { useEffect, useState } from 'react';
import { getAllProjects } from '../services/api';

const ProjectList = ({ token, onSelectProject }) => {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedProjectId, setSelectedProjectId] = useState(null);

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
    setSelectedProjectId(projectId);
    onSelectProject && onSelectProject(projectId);
  };

  if (loading) {
    return <div className="loading">Loading projects...</div>;
  }

  if (error) {
    return <div className="error">Error: {error}</div>;
  }

  return (
    <div className="projects-list">
      {projects.map((project) => (
        <div 
          key={project.uuid} 
          className={`project-card ${selectedProjectId === project.uuid ? 'selected' : ''}`}
          onClick={() => handleProjectClick(project.uuid)}
        >
          <div className="project-info">
            <div className="project-name">{project.name}</div>
            <div className="project-description">{project.description || 'No description'}</div>
          </div>
          <div className="project-uuid">
            {project.uuid}
          </div>
        </div>
      ))}

      <style jsx>{`
        .projects-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .project-card {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px;
          background: #f8f9fa;
          border-radius: 6px;
          transition: all 0.2s;
          cursor: pointer;
        }

        .project-card:hover {
          background: #f1f3f5;
        }

        .project-card.selected {
          background: #e7f5ff;
          border: 1px solid #339af0;
        }

        .project-info {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .project-name {
          font-weight: 500;
          color: #212529;
        }

        .project-description {
          font-size: 0.875rem;
          color: #6c757d;
        }

        .project-uuid {
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

export default ProjectList;
