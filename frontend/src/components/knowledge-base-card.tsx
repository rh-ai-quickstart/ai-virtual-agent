import { KnowledgeBaseWithStatus } from '@/types';
import { getStatusColor, getStatusLabel } from '@/utils/knowledge-base-status';
import {
  Card,
  CardHeader,
  CardTitle,
  CardBody,
  CardExpandableContent,
  Dropdown,
  DropdownList,
  DropdownItem,
  MenuToggle,
  MenuToggleElement,
  Title,
  Flex,
  FlexItem,
  Label,
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Icon,
} from '@patternfly/react-core';
import { EllipsisVIcon, TrashIcon } from '@patternfly/react-icons';
import { useState, Fragment } from 'react';

interface KnowledgeBaseCardProps {
  knowledgeBase: KnowledgeBaseWithStatus;
  onDelete?: (vectorDbName: string) => void;
  isDeleting?: boolean;
}

export function KnowledgeBaseCard({
  knowledgeBase,
  onDelete,
  isDeleting = false,
}: KnowledgeBaseCardProps) {
  const [dropdownOpen, setDropdownOpen] = useState<boolean>(false);
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const [modalOpen, setModalOpen] = useState<boolean>(false);

  const onExpand = () => setIsExpanded(!isExpanded);

  const toggleModal = () => {
    setModalOpen(!modalOpen);
  };

  const handleDeleteKnowledgeBase = () => {
    if (knowledgeBase.vector_db_name) {
      onDelete?.(knowledgeBase.vector_db_name);
    }
  };

  const dropdownItems = (
    <>
      <DropdownItem
        isDanger
        icon={<TrashIcon />}
        value={0}
        key="delete"
        onClick={() => {
          toggleModal();
          setDropdownOpen(false);
        }}
      >
        Delete
      </DropdownItem>
    </>
  );
  const headerActions = (
    <Fragment>
      <Dropdown
        isOpen={dropdownOpen}
        onOpenChange={(isOpen: boolean) => setDropdownOpen(isOpen)}
        toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
          <MenuToggle
            ref={toggleRef}
            aria-label="kebab dropdown toggle"
            variant="plain"
            onClick={(e) => {
              e.stopPropagation(); // Prevent header click
              setDropdownOpen(!dropdownOpen);
            }}
            isExpanded={dropdownOpen}
            icon={
              <Icon iconSize="lg">
                <EllipsisVIcon />
              </Icon>
            }
          />
        )}
        shouldFocusToggleOnSelect
        popperProps={{ position: 'right' }}
      >
        <DropdownList>{dropdownItems}</DropdownList>
      </Dropdown>
      <Modal
        isOpen={modalOpen}
        onClose={toggleModal}
        variant="small"
        aria-labelledby="delete-kb-modal-title"
        aria-describedby="delete-kb-modal-desc"
      >
        <ModalHeader title="Delete Knowledge Base" labelId="delete-kb-modal-title" />
        <ModalBody id="delete-kb-modal-desc">
          Are you sure you want to delete this knowledge base? This action cannot be undone.
        </ModalBody>
        <ModalFooter>
          <Button isLoading={isDeleting} onClick={handleDeleteKnowledgeBase} variant="danger">
            Delete
          </Button>
          <Button variant="link" onClick={toggleModal}>
            Cancel
          </Button>
        </ModalFooter>
      </Modal>
    </Fragment>
  );

  return (
    <Card
      id={`expandable-kb-card-${knowledgeBase.vector_db_name}`}
      isExpanded={isExpanded}
      className="pf-v6-u-mb-md"
    >
      <CardHeader
        actions={{ actions: headerActions }}
        onExpand={onExpand}
        toggleButtonProps={{
          id: `toggle-kb-button-${knowledgeBase.vector_db_name}`,
          'aria-label': 'Details',
          'aria-labelledby': `expandable-kb-title-${knowledgeBase.vector_db_name} toggle-kb-button-${knowledgeBase.vector_db_name}`,
          'aria-expanded': isExpanded,
        }}
      >
        <CardTitle id={`expandable-kb-title-${knowledgeBase.vector_db_name}`}>
          <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapSm' }}>
            <FlexItem>
              <Title className="pf-v6-u-mb-0" headingLevel="h2">
                {knowledgeBase.name}
              </Title>
            </FlexItem>
            <FlexItem>
              <Title className="pf-v6-u-text-color-subtle pf-v6-u-mb-0" headingLevel="h5">
                {knowledgeBase.embedding_model}
              </Title>
            </FlexItem>
            <FlexItem>
              <Label color={getStatusColor(knowledgeBase.status)}>
                {getStatusLabel(knowledgeBase.status)}
              </Label>
            </FlexItem>
          </Flex>
        </CardTitle>
      </CardHeader>
      <CardExpandableContent>
        <CardBody>
          <Flex direction={{ default: 'column' }}>
            <FlexItem>
              <span className="pf-v6-u-text-color-subtle">Version: </span>
              {knowledgeBase.version}
            </FlexItem>
            <FlexItem>
              <span className="pf-v6-u-text-color-subtle">Provider: </span>
              {knowledgeBase.provider_id}
            </FlexItem>
            <FlexItem>
              <span className="pf-v6-u-text-color-subtle">Vector DB: </span>
              {knowledgeBase.vector_db_name}
            </FlexItem>
            <FlexItem>
              <span className="pf-v6-u-text-color-subtle">External: </span>
              {knowledgeBase.is_external ? 'Yes' : 'No'}
            </FlexItem>
            <FlexItem>
              <span className="pf-v6-u-text-color-subtle">Source: </span>
              {knowledgeBase.source}
            </FlexItem>
            <FlexItem>
              <span className="pf-v6-u-text-color-subtle">Configuration: </span>
              {typeof knowledgeBase.source_configuration === 'string'
                ? knowledgeBase.source_configuration
                : JSON.stringify(knowledgeBase.source_configuration, null, 2)}
            </FlexItem>
          </Flex>
        </CardBody>
      </CardExpandableContent>
    </Card>
  );
}
