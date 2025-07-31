import React from 'react';
import { FormGroup, FormHelperText, Slider } from '@patternfly/react-core';
import { FormFieldProps, FormFieldSliderProps } from '@/types/forms';

const FormFieldSlider: React.FC<FormFieldSliderProps> = ({
  form,
  name,
  label,
  helperText,
  min,
  max,
  step,
  handleSliderChange,
}) => (
  <form.Field name={name}>
    {(field: FormFieldProps) => (
      <FormGroup
        label={label}
        fieldId={name}
        className="wide-input-slider"
        style={{ marginBottom: 24, marginLeft: 15 }}
      >
        <FormHelperText>{helperText}</FormHelperText>
        <div style={{ maxWidth: 1050 }}>
          <Slider
            value={field.state.value}
            min={min}
            max={max}
            step={step}
            isInputVisible
            inputValue={field.state.value}
            onChange={(event, value, inputValue, setLocalInputValue) =>
              handleSliderChange(
                event,
                field,
                value,
                inputValue,
                { min, max, step },
                setLocalInputValue
              )
            }
            aria-label={label}
          />
        </div>
      </FormGroup>
    )}
  </form.Field>
);

export default FormFieldSlider;
