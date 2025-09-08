import { Nav, NavItem, NavList, Page, PageSidebar, PageSidebarBody } from '@patternfly/react-core';
import { createFileRoute, Link, Outlet, useLocation } from '@tanstack/react-router';
import { Masthead } from '../../../components/masthead';
import { UserIcon } from '@patternfly/react-icons';

export const Route = createFileRoute('/_protected/config')({
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
            <NavItem itemId={0} isActive={location.pathname == '/config/profile'} to="#">
              <Link to="/config/profile">
                <UserIcon style={{ marginRight: '8px' }} />
                User Profile
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
