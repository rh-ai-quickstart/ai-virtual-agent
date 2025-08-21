import type { ReactNode } from 'react';
import { HomeIcon, BriefcaseIcon, BuildingIcon, PlaneIcon } from '@patternfly/react-icons';

// Suite icon mapping shared across the app
export const SUITE_ICONS: Record<string, ReactNode> = {
  core_banking: <HomeIcon style={{ color: '#8A2BE2' }} />,
  wealth_management: <BriefcaseIcon style={{ color: '#8B4513' }} />,
  business_banking: <BuildingIcon style={{ color: '#4169E1' }} />,
  travel_hospitality: <PlaneIcon style={{ color: '#FF6B35' }} />,
};

// Category icon mapping (used on Templates page)
export const CATEGORY_ICONS: Record<string, ReactNode> = {
  banking: <HomeIcon style={{ color: '#8A2BE2', fontSize: '24px' }} />,
  travel: <PlaneIcon style={{ color: '#FF6B35', fontSize: '24px' }} />,
  default: <HomeIcon style={{ color: '#6A6E73', fontSize: '24px' }} />,
};
