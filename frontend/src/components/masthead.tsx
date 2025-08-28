import {
  Flex,
  FlexItem,
  MastheadBrand,
  MastheadContent,
  MastheadMain,
  MastheadToggle,
  Nav,
  NavItem,
  NavList,
  Masthead as PFMasthead,
  PageToggleButton,
  Title,
  ToggleGroup,
  ToggleGroupItem,
  Toolbar,
  ToolbarContent,
  ToolbarGroup,
  ToolbarItem,
} from '@patternfly/react-core';
import React from 'react';

import { Link, useLocation } from '@tanstack/react-router';
import { BarsIcon, SunIcon, MoonIcon, ChatIcon, CogIcon } from '@patternfly/react-icons';
import { useCurrentUser } from '@/contexts/UserContext';

export const themeStorageKey = 'app-theme';

interface MastheadProps {
  showSidebarToggle?: boolean;
  isSidebarOpen?: boolean;
  onSidebarToggle?: () => void;
}

export function Masthead({
  showSidebarToggle = false,
  isSidebarOpen = false,
  onSidebarToggle,
}: MastheadProps) {
  const location = useLocation();
  const { currentUser } = useCurrentUser();
  const [isDarkTheme, setIsDarkTheme] = React.useState(false);

  // Load preferred theme from localstorage
  React.useMemo(() => {
    const isDarkThemeSaved = localStorage.getItem(themeStorageKey);
    if (isDarkThemeSaved === null) return;

    const isDark = JSON.parse(isDarkThemeSaved) as boolean;
    setIsDarkTheme(isDark);

    if (!isDark) return;

    const htmlElement = document.querySelector('html');
    if (!htmlElement) return;

    htmlElement.classList.toggle('pf-v6-theme-dark', true);
  }, []);

  const toggleDarkTheme = (
    _event: MouseEvent | React.MouseEvent<Element, MouseEvent> | React.KeyboardEvent<Element>,
    selected: boolean
  ) => {
    const darkThemeToggleClicked = !selected === isDarkTheme;
    const htmlElement = document.querySelector('html');
    if (htmlElement) {
      htmlElement.classList.toggle('pf-v6-theme-dark', darkThemeToggleClicked);
    }
    setIsDarkTheme(darkThemeToggleClicked);
    localStorage.setItem(themeStorageKey, JSON.stringify(darkThemeToggleClicked));
  };

  const nav = (
    <Nav variant="horizontal" aria-label="Main Nav">
      <NavList>
        <NavItem itemId={0} isActive={location.pathname == '/'} to="#">
          <Link to="/" search={{ agentId: '' }}>
            <Flex
              direction={{ default: 'row' }}
              alignItems={{ default: 'alignItemsCenter' }}
              gap={{ default: 'gapSm' }}
            >
              <FlexItem>
                <ChatIcon />
              </FlexItem>
              <FlexItem>Chat</FlexItem>
            </Flex>
          </Link>
        </NavItem>
        {/* Only show Config navigation for admin users */}
        {currentUser?.role === 'admin' && (
          <NavItem
            icon={<CogIcon />}
            itemId={1}
            isActive={location.pathname.startsWith('/config/')}
            to="#"
          >
            <Link to="/config/agents">
              <Flex
                direction={{ default: 'row' }}
                alignItems={{ default: 'alignItemsCenter' }}
                gap={{ default: 'gapSm' }}
              >
                <FlexItem>
                  <CogIcon />
                </FlexItem>
                <FlexItem>Config</FlexItem>
              </Flex>
            </Link>
          </NavItem>
        )}
      </NavList>
    </Nav>
  );

  const toggle =
    showSidebarToggle && onSidebarToggle ? (
      <PageToggleButton
        variant="plain"
        aria-label="Global navigation"
        isSidebarOpen={isSidebarOpen}
        onSidebarToggle={onSidebarToggle}
        id="main-padding-nav-toggle"
      >
        <BarsIcon />
      </PageToggleButton>
    ) : null;

  const toolbar = (
    <Toolbar
      inset={{
        default: 'insetSm',
        md: 'insetMd',
        lg: 'insetLg',
        xl: 'insetXl',
        '2xl': 'inset2xl',
      }}
      isFullHeight
    >
      <ToolbarContent>
        <ToolbarGroup align={{ default: 'alignStart' }}>
          <ToolbarItem>{nav}</ToolbarItem>
        </ToolbarGroup>
        <ToolbarGroup align={{ default: 'alignEnd' }}>
          <ToolbarItem>
            <ToggleGroup aria-label="Dark theme toggle group">
              <ToggleGroupItem
                aria-label="light theme toggle"
                icon={<SunIcon />}
                isSelected={!isDarkTheme}
                onChange={toggleDarkTheme}
              />
              <ToggleGroupItem
                aria-label="dark theme toggle"
                icon={<MoonIcon />}
                isSelected={isDarkTheme}
                onChange={toggleDarkTheme}
              />
            </ToggleGroup>
          </ToolbarItem>
        </ToolbarGroup>
      </ToolbarContent>
    </Toolbar>
  );

  return (
    <PFMasthead>
      <MastheadMain>
        {showSidebarToggle && <MastheadToggle>{toggle}</MastheadToggle>}
        <MastheadBrand data-codemods>
          <Title headingLevel="h1">AI Virtual Agent</Title>
        </MastheadBrand>
      </MastheadMain>
      <MastheadContent>{toolbar}</MastheadContent>
    </PFMasthead>
  );
}
