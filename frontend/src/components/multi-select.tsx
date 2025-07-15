import {
  Button,
  Label,
  LabelGroup,
  MenuToggle,
  MenuToggleElement,
  SelectOptionProps as PFSelectOptionProps,
  Select,
  SelectList,
  SelectOption,
  TextInputGroup,
  TextInputGroupMain,
  TextInputGroupUtilities,
} from '@patternfly/react-core';
import TimesIcon from '@patternfly/react-icons/dist/esm/icons/times-icon';
import React, { useEffect, useRef, useState } from 'react';

export interface CustomSelectOptionProps extends PFSelectOptionProps {
  value: string;
  children: string;
}

interface MultiSelectProps {
  id: string;
  value: string[];
  options: CustomSelectOptionProps[];
  onBlur: () => void;
  onChange: (newValue: string[]) => void;
  ariaLabel?: string;
  isDisabled?: boolean;
  placeholder?: string;
}

const enhancedMultiSelectStyles = `
  .multi-select-enhanced .pf-v5-c-menu-toggle {
    border: 2px solid #e2e8f0;
    border-radius: 12px;
    transition: all 0.3s ease;
    background: white;
    min-height: 48px;
  }
  
  .multi-select-enhanced .pf-v5-c-menu-toggle:hover {
    border-color: #cbd5e1;
  }
  
  .multi-select-enhanced .pf-v5-c-menu-toggle.pf-m-expanded,
  .multi-select-enhanced .pf-v5-c-menu-toggle:focus {
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    outline: none;
  }
  
  .multi-select-enhanced .pf-v5-c-text-input-group__main {
    padding: 0.5rem 0.75rem;
  }
  
  .multi-select-enhanced .pf-v5-c-text-input-group__text-input {
    border: none;
    outline: none;
    font-size: 0.875rem;
    color: #1e293b;
  }
  
  .multi-select-enhanced .pf-v5-c-text-input-group__text-input::placeholder {
    color: #94a3b8;
    font-style: italic;
  }
  
  .multi-select-enhanced .pf-v5-c-label-group {
    gap: 0.375rem;
    margin-bottom: 0.25rem;
  }
  
  .enhanced-select-label {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 0.25rem 0.5rem;
    font-size: 0.75rem;
    font-weight: 500;
    box-shadow: 0 2px 4px rgba(102, 126, 234, 0.2);
    transition: all 0.2s ease;
  }
  
  .enhanced-select-label:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
  }
  
  .enhanced-select-label .pf-v5-c-label__content {
    color: white;
  }
  
  .enhanced-select-label .pf-v5-c-button {
    color: white;
    border: none;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 4px;
    padding: 0.125rem;
    margin-left: 0.25rem;
    transition: all 0.2s ease;
  }
  
  .enhanced-select-label .pf-v5-c-button:hover {
    background: rgba(255, 255, 255, 0.3);
  }
  
  .clear-button-enhanced {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
    border: none;
    border-radius: 6px;
    padding: 0.375rem;
    transition: all 0.2s ease;
    margin-right: 0.5rem;
  }
  
  .clear-button-enhanced:hover {
    background: rgba(239, 68, 68, 0.2);
    transform: scale(1.05);
  }
  
  .multi-select-enhanced .pf-v5-c-select__menu {
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
    overflow: hidden;
    margin-top: 0.25rem;
  }
  
  .multi-select-enhanced .pf-v5-c-select__menu-item {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid #f1f5f9;
    transition: all 0.2s ease;
    font-size: 0.875rem;
  }
  
  .multi-select-enhanced .pf-v5-c-select__menu-item:last-child {
    border-bottom: none;
  }
  
  .multi-select-enhanced .pf-v5-c-select__menu-item:hover {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  }
  
  .multi-select-enhanced .pf-v5-c-select__menu-item.pf-m-selected {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    font-weight: 500;
  }
  
  .multi-select-enhanced .pf-v5-c-select__menu-item.pf-m-focused {
    background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%);
    color: #3730a3;
  }
  
  .multi-select-enhanced .pf-v5-c-select__menu-item.pf-m-selected.pf-m-focused {
    background: linear-gradient(135deg, #5b21b6 0%, #6d28d9 100%);
    color: white;
  }
  
  .multi-select-enhanced .pf-v5-c-select__menu-item[aria-disabled="true"] {
    color: #94a3b8;
    background: #f8fafc;
    cursor: not-allowed;
  }
  
  .select-option-enhanced {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  
  .select-option-icon {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75rem;
    color: white;
    flex-shrink: 0;
  }
  
  .select-option-content {
    flex: 1;
  }
  
  .select-option-name {
    font-weight: 500;
    color: inherit;
  }
  
  .no-results-item {
    font-style: italic;
    color: #64748b;
    text-align: center;
    padding: 1rem;
  }
`;

export function MultiSelect({
  id,
  value,
  options,
  onBlur,
  onChange,
  ariaLabel,
  isDisabled = false,
  placeholder = 'Select options...',
}: MultiSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [inputValue, setInputValue] = useState<string>('');
  const [filteredOptions, setFilteredOptions] = useState<CustomSelectOptionProps[]>(options);
  const [focusedItemIndex, setFocusedItemIndex] = useState<number | null>(null);
  const [activeItemId, setActiveItemId] = useState<string | null>(null);
  const textInputRef = useRef<HTMLInputElement>(null);

  const NO_RESULTS_VALUE = '___no-results___';

  useEffect(() => {
    if (!isOpen) {
      if (!inputValue) setFilteredOptions(options);
      return;
    }

    let newFilteredOptions: CustomSelectOptionProps[];

    if (inputValue) {
      newFilteredOptions = options.filter((menuItem) =>
        String(menuItem.children).toLowerCase().includes(inputValue.toLowerCase())
      );

      if (!newFilteredOptions.length) {
        newFilteredOptions = [
          {
            isAriaDisabled: true,
            children: `No results found for "${inputValue}"`,
            value: NO_RESULTS_VALUE,
            id: `${id}-${NO_RESULTS_VALUE}`,
          },
        ];
      }
    } else {
      newFilteredOptions = options;
    }
    setFilteredOptions(newFilteredOptions);
  }, [inputValue, options, isOpen, id]);

  const createItemId = (optionValue: string | number | undefined): string => {
    const stringValue = String(optionValue || '');
    return `${id}-option-${stringValue.replace(/\s+/g, '-')}`;
  };

  const setActiveAndFocusedItem = (itemIndex: number) => {
    setFocusedItemIndex(itemIndex);
    const focusedItem = filteredOptions[itemIndex];
    if (focusedItem && focusedItem.value && focusedItem.value !== NO_RESULTS_VALUE) {
      setActiveItemId(createItemId(focusedItem.value));
    } else {
      setActiveItemId(null);
    }
  };

  const resetActiveAndFocusedItem = () => {
    setFocusedItemIndex(null);
    setActiveItemId(null);
  };

  const closeMenu = (runOnBlur = true) => {
    setIsOpen(false);
    resetActiveAndFocusedItem();
    if (runOnBlur) {
      onBlur();
    }
  };

  const onInputClick = () => {
    if (isDisabled) return;
    if (!isOpen) {
      setIsOpen(true);
    }
  };

  const handlePFSelect = (
    _event: React.MouseEvent | React.ChangeEvent | undefined,
    selectionValue: string | number | undefined
  ) => {
    if (isDisabled || typeof selectionValue !== 'string' || selectionValue === NO_RESULTS_VALUE) {
      return;
    }

    const clickedValue = selectionValue;
    const newSelectedState = value.includes(clickedValue)
      ? value.filter((v) => v !== clickedValue)
      : [...value, clickedValue];

    onChange(newSelectedState);
    textInputRef.current?.focus();
  };

  const onTextInputChange = (_event: React.FormEvent<HTMLInputElement>, newInputValue: string) => {
    setInputValue(newInputValue);
    if (!isOpen && newInputValue) {
      setIsOpen(true);
    }
    resetActiveAndFocusedItem();
  };

  const handleMenuArrowKeys = (key: string) => {
    if (
      isDisabled ||
      !isOpen ||
      filteredOptions.every((opt) => opt.isAriaDisabled || opt.isDisabled)
    ) {
      return;
    }

    let indexToFocus = focusedItemIndex === null ? -1 : focusedItemIndex;

    if (key === 'ArrowUp') {
      indexToFocus = indexToFocus <= 0 ? filteredOptions.length - 1 : indexToFocus - 1;
    } else if (key === 'ArrowDown') {
      indexToFocus = indexToFocus >= filteredOptions.length - 1 ? 0 : indexToFocus + 1;
    }

    let attempts = 0;
    while (
      attempts < filteredOptions.length &&
      (filteredOptions[indexToFocus].isAriaDisabled || filteredOptions[indexToFocus].isDisabled)
    ) {
      if (key === 'ArrowUp') {
        indexToFocus = indexToFocus <= 0 ? filteredOptions.length - 1 : indexToFocus - 1;
      } else {
        indexToFocus = indexToFocus >= filteredOptions.length - 1 ? 0 : indexToFocus + 1;
      }
      attempts++;
    }
    if (attempts < filteredOptions.length) {
      setActiveAndFocusedItem(indexToFocus);
    }
  };

  const onInputKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (isDisabled) return;

    const focusedItem = focusedItemIndex !== null ? filteredOptions[focusedItemIndex] : null;

    switch (event.key) {
      case 'Enter':
        event.preventDefault();
        if (
          isOpen &&
          focusedItem &&
          focusedItem.value !== NO_RESULTS_VALUE &&
          !focusedItem.isAriaDisabled &&
          !focusedItem.isDisabled
        ) {
          handlePFSelect(undefined, focusedItem.value);
        } else if (!isOpen) {
          setIsOpen(true);
        }
        break;
      case 'ArrowUp':
      case 'ArrowDown':
        event.preventDefault();
        if (!isOpen && filteredOptions.length > 0) setIsOpen(true);
        handleMenuArrowKeys(event.key);
        break;
      case 'Escape':
        event.preventDefault();
        closeMenu();
        break;
      case 'Tab':
        closeMenu();
        break;
      case 'Backspace':
        if (!inputValue && value.length > 0) {
          event.preventDefault();
          onChange(value.slice(0, -1));
        }
        break;
    }
  };

  const onToggleClick = () => {
    if (isDisabled) return;
    setIsOpen(!isOpen);
    if (!isOpen) {
      textInputRef.current?.focus();
    } else {
      onBlur();
    }
  };

  const onClearButtonClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onChange([]);
    setInputValue('');
    resetActiveAndFocusedItem();
    textInputRef.current?.focus();
    if (!isOpen) setIsOpen(true);
  };

  const toggle = (toggleRef: React.Ref<MenuToggleElement>) => (
    <MenuToggle
      variant="typeahead"
      aria-label={ariaLabel || 'Multi typeahead menu toggle'}
      onClick={onToggleClick}
      innerRef={toggleRef}
      isExpanded={isOpen}
      isDisabled={isDisabled}
      isFullWidth
    >
      <TextInputGroup isPlain isDisabled={isDisabled}>
        <TextInputGroupMain
          value={inputValue}
          onClick={onInputClick}
          onChange={onTextInputChange}
          onKeyDown={onInputKeyDown}
          id={`${id}-input`}
          autoComplete="off"
          innerRef={textInputRef}
          placeholder={value.length > 0 ? '' : placeholder}
          {...(activeItemId && { 'aria-activedescendant': activeItemId })}
          role="combobox"
          isExpanded={isOpen}
          aria-controls={`${id}-listbox`}
        >
          <LabelGroup aria-label="Current selections" numLabels={5}>
            {value.map((selectedValue) => {
              const option = options.find((opt) => opt.value === selectedValue);
              return (
                <Label
                  key={selectedValue}
                  variant="outline"
                  onClose={(ev) => {
                    ev.stopPropagation();
                    handlePFSelect(undefined, selectedValue);
                  }}
                  isDisabled={isDisabled}
                  className="enhanced-select-label"
                >
                  {option?.children || selectedValue}
                </Label>
              );
            })}
          </LabelGroup>
        </TextInputGroupMain>
        {(value.length > 0 || inputValue) && (
          <TextInputGroupUtilities>
            <Button
              variant="plain"
              onClick={onClearButtonClick}
              aria-label="Clear selections and input"
              isDisabled={isDisabled}
              icon={<TimesIcon />}
              className="clear-button-enhanced"
            />
          </TextInputGroupUtilities>
        )}
      </TextInputGroup>
    </MenuToggle>
  );

  return (
    <>
      <style>{enhancedMultiSelectStyles}</style>
      <div className="multi-select-enhanced">
        <Select
          id={id}
          isOpen={isOpen}
          selected={value}
          onSelect={handlePFSelect}
          onOpenChange={(newIsOpenState) => {
            setIsOpen(newIsOpenState);
            if (!newIsOpenState) {
              closeMenu();
            }
          }}
          toggle={toggle}
        >
          <SelectList isAriaMultiselectable id={`${id}-listbox`}>
            {filteredOptions.map((option, index) => (
              <SelectOption
                key={option.id || option.value || index}
                isFocused={focusedItemIndex === index}
                isSelected={value.includes(option.value)}
                value={option.value}
                isDisabled={option.isDisabled || option.isAriaDisabled}
                id={
                  option.id && option.id !== NO_RESULTS_VALUE ? option.id : createItemId(option.value)
                }
                className={option.value === NO_RESULTS_VALUE ? 'no-results-item' : ''}
              >
                {option.value === NO_RESULTS_VALUE ? (
                  <div className="no-results-item">
                    {option.children}
                  </div>
                ) : (
                  <div className="select-option-enhanced">
                    <div className="select-option-icon">
                      {option.value.includes('builtin::') ? '🔧' : '📦'}
                    </div>
                    <div className="select-option-content">
                      <div className="select-option-name">
                        {option.children}
                      </div>
                    </div>
                  </div>
                )}
              </SelectOption>
            ))}
          </SelectList>
        </Select>
      </div>
    </>
  );
}