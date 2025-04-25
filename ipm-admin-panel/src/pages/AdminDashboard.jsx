import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import ProjectList from "../components/ProjectList";
import GetUsers from "../components/GetUsers";
import ProjectCreate from "../components/ProjectCreate";
import UserCreate from "../components/UserCreate";
import ProjectUserMapping from "../components/ProjectUserMapping";
import ProjectItemMapping from "../components/ProjectItemMapping";
import ItemCreate from "../components/ItemCreate";
import KhatabookCreate from "../components/KhatabookCreate";
import { logoutUser } from "../services/api";
import "../styles/AdminDashboard.css";

const AdminDashboard = ({ token }) => {
  const navigate = useNavigate();
  const [showProjectCreate, setShowProjectCreate] = useState(false);
  const [showUserCreate, setShowUserCreate] = useState(false);
  const [showUserMapping, setShowUserMapping] = useState(false);
  const [showItemMapping, setShowItemMapping] = useState(false);
  const [showItemCreate, setShowItemCreate] = useState(false);
  const [showKhatabookCreate, setShowKhatabookCreate] = useState(false);
  const [selectedProject, setSelectedProject] = useState(null);

  useEffect(() => {
    try {
      const userData = localStorage.getItem("user");
      if (userData) {
        const user = JSON.parse(userData);
        if (user.role !== "superadmin" && user.role !== "admin") {
          navigate("/admin-dashboard");
        }
      } else {
        navigate("/login");
      }
    } catch (error) {
      console.error("Error parsing user data:", error);
      navigate("/login");
    }
  }, [navigate]);

  const handleCreateUserClick = () => setShowUserCreate(true);
  const handleCreateProjectClick = () => setShowProjectCreate(true);
  const handleCloseProjectCreate = () => setShowProjectCreate(false);
  const handleCloseUserCreate = () => setShowUserCreate(false);
  const handleUserMappingClick = () => setShowUserMapping(true);
  const handleCloseUserMapping = () => setShowUserMapping(false);
  const handleItemMappingClick = () => setShowItemMapping(true);
  const handleCloseItemMapping = () => setShowItemMapping(false);
  const handleCreateItemClick = () => setShowItemCreate(true);
  const handleCloseItemCreate = () => setShowItemCreate(false);
  const handleCreateKhatabookClick = () => setShowKhatabookCreate(true);
  const handleCloseKhatabookCreate = () => setShowKhatabookCreate(false);

  const handleLogoutClick = async () => {
    try {
      const userData = JSON.parse(localStorage.getItem("user") || "{}");
      await logoutUser(userData.uuid, "web", token); // Using 'web' as device ID for browser sessions
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      navigate("/login");
    } catch (error) {
      console.error("Logout failed:", error);
      // Still clear local storage and redirect even if the API call fails
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      navigate("/login");
    }
  };

  const handleProjectItemListClick = () => {
    if (selectedProject) {
      navigate(`/project-details/${selectedProject}`);
    } else {
      alert("Please select a project first");
    }
  };

  const handleProjectSelect = (projectId) => {
    setSelectedProject(projectId);
  };

  return (
    <div className="admin-dashboard">
      <header className="dashboard-header">
        <div className="header-content">
          <h1>Admin Panel</h1>
          <nav className="nav-links">
            <button onClick={handleProjectItemListClick}>Map Project Item List</button>
            <button onClick={handleUserMappingClick}>Map Users to Projects</button>
            <button onClick={handleItemMappingClick}>Map Items to Projects</button>
            <button onClick={handleLogoutClick}>Logout</button>
          </nav>
        </div>
      </header>

      <div className="action-buttons">
        <button className="create-new-btn" onClick={handleCreateKhatabookClick}>
          Create Khatabook Entry
        </button>
        <button className="create-new-btn" onClick={handleCreateItemClick}>
          Create New Item
        </button>
        <button className="create-new-btn" onClick={handleCreateProjectClick}>
          Create New Project
        </button>
        <button className="create-new-btn" onClick={handleCreateUserClick}>
          Create New User
        </button>
      </div>

      {/* Main Content */}
      <div className="dashboard-content">
        {/* Projects Section */}
        <section className="section-projects">
          <div className="section-header">
            <h2>Projects</h2>
          </div>
          <ProjectList
            token={localStorage.getItem("token")}
            onSelectProject={handleProjectSelect}
          />
        </section>
      </div>
      {/* Users Section */}
      <section className="section-users">
        <div className="section-header">
          <h2>Users</h2>
        </div>
        <GetUsers token={localStorage.getItem("token")} />
      </section>

      {/* Modals */}
      {showProjectCreate && (
        <div className="modal">
          <div className="modal-content">
            <button className="close-btn" onClick={handleCloseProjectCreate}>
              X
            </button>
            <ProjectCreate token={localStorage.getItem("token")} />
          </div>
        </div>
      )}

      {showUserCreate && (
        <div className="modal">
          <div className="modal-content">
            <button className="close-btn" onClick={handleCloseUserCreate}>
              X
            </button>
            <UserCreate token={localStorage.getItem("token")} />
          </div>
        </div>
      )}

      {showUserMapping && (
        <div className="modal">
          <div className="modal-content">
            <button className="close-btn" onClick={handleCloseUserMapping}>
              X
            </button>
            <ProjectUserMapping token={localStorage.getItem("token")} />
          </div>
        </div>
      )}

      {showItemMapping && (
        <div className="modal">
          <div className="modal-content">
            <button className="close-btn" onClick={handleCloseItemMapping}>
              X
            </button>
            <ProjectItemMapping token={localStorage.getItem("token")} />
          </div>
        </div>
      )}

      {showItemCreate && (
        <div className="modal">
          <div className="modal-content">
            <button className="close-btn" onClick={handleCloseItemCreate}>
              X
            </button>
            <ItemCreate
              token={localStorage.getItem("token")}
              onClose={handleCloseItemCreate}
              onItemCreated={() => {
                alert("Item created successfully");
              }}
            />
          </div>
        </div>
      )}

      {showKhatabookCreate && (
        <div className="modal">
          <div className="modal-content">
            <button className="close-btn" onClick={handleCloseKhatabookCreate}>
              X
            </button>
            <KhatabookCreate
              token={localStorage.getItem("token")}
              onClose={handleCloseKhatabookCreate}
              onSuccess={() => {
                alert("Khatabook entry created successfully");
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminDashboard;
