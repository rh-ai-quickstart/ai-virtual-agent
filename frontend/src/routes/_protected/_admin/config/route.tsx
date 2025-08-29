import { Nav, NavItem, NavList, Page, PageSidebar, PageSidebarBody } from '@patternfly/react-core';
import { RobotIcon, BookIcon, ServerIcon, UsersIcon } from '@patternfly/react-icons';
import { createFileRoute, Link, Outlet, useLocation } from '@tanstack/react-router';
import { Masthead } from '../../../../components/masthead';

export const Route = createFileRoute('/_protected/_admin/config')({
  component: ConfigLayout,
});

function ConfigLayout() {
  const location = useLocation();

  const masthead = <Masthead showSidebarToggle={false} />;

  const sidebar = (
    <PageSidebar isSidebarOpen={true} id="main-padding-sidebar">
      <PageSidebarBody>
        <Nav aria-label="Config Nav">
          <NavList>
            <NavItem itemId={0} isActive={location.pathname == '/config/agents'} to="#">
              <Link to="/config/agents">
                <RobotIcon style={{ marginRight: '8px' }} />
                Agents
              </Link>
            </NavItem>
            <NavItem itemId={1} isActive={location.pathname == '/config/knowledge-bases'} to="#">
              <Link to="/config/knowledge-bases">
                <BookIcon style={{ marginRight: '8px' }} />
                Knowledge Bases
              </Link>
            </NavItem>
            <NavItem itemId={2} isActive={location.pathname == '/config/mcp-servers'} to="#">
              <Link to="/config/mcp-servers">
                <ServerIcon style={{ marginRight: '8px' }} />
                MCP Servers
              </Link>
            </NavItem>
            <NavItem itemId={3} isActive={location.pathname == '/config/users'} to="#">
              <Link to="/config/users" search={{ userId: undefined }}>
                <UsersIcon style={{ marginRight: '8px' }} />
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
