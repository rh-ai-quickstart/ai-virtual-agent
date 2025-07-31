import { Nav, NavItem, NavList, Page, PageSidebar, PageSidebarBody } from '@patternfly/react-core';
import { createFileRoute, Link, Outlet, useLocation } from '@tanstack/react-router';
import React from 'react';
import { Masthead } from '../../components/masthead';

export const Route = createFileRoute('/config')({
  component: ConfigLayout,
});

function ConfigLayout() {
  const location = useLocation();
  const [isSidebarOpen, setIsSidebarOpen] = React.useState(true);

  const onSidebarToggle = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  const masthead = (
    <Masthead
      showSidebarToggle={true}
      isSidebarOpen={isSidebarOpen}
      onSidebarToggle={onSidebarToggle}
    />
  );

  const sidebar = (
    <PageSidebar isSidebarOpen={isSidebarOpen} id="main-padding-sidebar">
      <PageSidebarBody>
        <Nav aria-label="Config Nav">
          <NavList>
            <NavItem itemId={0} isActive={location.pathname == '/config/agents'} to="#">
              <Link to="/config/agents">Agents</Link>
            </NavItem>
            <NavItem itemId={1} isActive={location.pathname == '/config/knowledge-bases'} to="#">
              <Link to="/config/knowledge-bases">Knowledge Bases</Link>
            </NavItem>
            <NavItem itemId={2} isActive={location.pathname == '/config/mcp-servers'} to="#">
              <Link to="/config/mcp-servers">MCP Servers</Link>
            </NavItem>
            <NavItem itemId={3} isActive={location.pathname == '/config/users'} to="#">
              <Link to="/config/users" search={{ userId: undefined }}>
                Users
              </Link>
            </NavItem>
          </NavList>
        </Nav>
      </PageSidebarBody>
    </PageSidebar>
  );

  return (
    <Page sidebar={sidebar} mainContainerId={'config-page-container'} masthead={masthead}>
      <Outlet />
    </Page>
  );
}
