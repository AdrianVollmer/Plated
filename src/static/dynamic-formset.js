/**
 * DynamicFormset - A vanilla JavaScript class for managing Django formsets dynamically
 *
 * Features:
 * - Add new forms dynamically using empty_form template
 * - Delete forms (mark for deletion or remove new forms)
 * - Reorder forms with move up/down buttons
 * - Automatic management form updates
 * - Drag-and-drop reordering support
 */
class DynamicFormset {
    constructor(options) {
        this.prefix = options.prefix;
        this.formsetContainer = document.getElementById(options.containerID);
        this.addButton = document.getElementById(options.addButtonID);
        this.emptyFormTemplate = options.emptyFormTemplate;
        this.formClass = options.formClass || `${this.prefix}-form`;
        this.onFormAdded = options.onFormAdded || null;
        this.onFormDeleted = options.onFormDeleted || null;

        this.managementForm = {
            totalForms: document.getElementById(`id_${this.prefix}-TOTAL_FORMS`),
            initialForms: document.getElementById(`id_${this.prefix}-INITIAL_FORMS`),
            minNumForms: document.getElementById(`id_${this.prefix}-MIN_NUM_FORMS`),
            maxNumForms: document.getElementById(`id_${this.prefix}-MAX_NUM_FORMS`)
        };

        this.init();
    }

    init() {
        // Bind add button
        if (this.addButton) {
            this.addButton.addEventListener('click', (e) => {
                e.preventDefault();
                this.addForm();
            });
        }

        // Initialize existing forms
        this.updateFormIndices();
        this.attachFormHandlers();
        this.updateOrderFields();
    }

    addForm() {
        const totalForms = parseInt(this.managementForm.totalForms.value);

        // Clone the empty form template
        let newForm = this.emptyFormTemplate.replace(/__prefix__/g, totalForms);

        // Create a temporary container to parse HTML
        const temp = document.createElement('div');
        temp.innerHTML = newForm;
        const formElement = temp.firstElementChild;

        // Add the form to container
        this.formsetContainer.appendChild(formElement);

        // Update management form
        this.managementForm.totalForms.value = totalForms + 1;

        // Attach handlers to the new form
        this.attachFormHandlers(formElement);
        this.updateOrderFields();

        // Trigger callback if provided
        if (this.onFormAdded) {
            this.onFormAdded(formElement, totalForms);
        }

        // Scroll to the new form
        formElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    deleteForm(formElement) {
        const deleteCheckbox = formElement.querySelector(`input[name$="-DELETE"]`);

        if (deleteCheckbox) {
            // Existing form - mark for deletion
            deleteCheckbox.checked = true;
            formElement.style.display = 'none';
        } else {
            // New form - remove from DOM
            formElement.remove();
            this.updateFormIndices();
        }

        this.updateOrderFields();

        // Trigger callback if provided
        if (this.onFormDeleted) {
            this.onFormDeleted(formElement);
        }
    }

    moveFormUp(formElement) {
        const previousForm = formElement.previousElementSibling;
        if (previousForm && previousForm.classList.contains(this.formClass)) {
            this.formsetContainer.insertBefore(formElement, previousForm);
            this.updateOrderFields();
            this.highlightMovedForm(formElement);
        }
    }

    moveFormDown(formElement) {
        const nextForm = formElement.nextElementSibling;
        if (nextForm && nextForm.classList.contains(this.formClass)) {
            this.formsetContainer.insertBefore(nextForm, formElement);
            this.updateOrderFields();
            this.highlightMovedForm(formElement);
        }
    }

    highlightMovedForm(formElement) {
        // Add highlight class
        formElement.classList.add('form-moved-highlight');

        // Scroll to the form smoothly
        formElement.scrollIntoView({
            behavior: 'smooth',
            block: 'nearest'
        });

        // Remove highlight after animation completes
        setTimeout(() => {
            formElement.classList.remove('form-moved-highlight');
        }, 800);
    }

    attachFormHandlers(container = null) {
        const forms = container ? [container] : this.formsetContainer.querySelectorAll(`.${this.formClass}`);

        forms.forEach(form => {
            // Delete button
            const deleteBtn = form.querySelector('.delete-form-btn');
            if (deleteBtn && !deleteBtn.hasAttribute('data-bound')) {
                deleteBtn.setAttribute('data-bound', 'true');
                deleteBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    if (confirm('Are you sure you want to delete this item?')) {
                        this.deleteForm(form);
                    }
                });
            }

            // Move up button
            const moveUpBtn = form.querySelector('.move-up-btn');
            if (moveUpBtn && !moveUpBtn.hasAttribute('data-bound')) {
                moveUpBtn.setAttribute('data-bound', 'true');
                moveUpBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.moveFormUp(form);
                });
            }

            // Move down button
            const moveDownBtn = form.querySelector('.move-down-btn');
            if (moveDownBtn && !moveDownBtn.hasAttribute('data-bound')) {
                moveDownBtn.setAttribute('data-bound', 'true');
                moveDownBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.moveFormDown(form);
                });
            }
        });
    }

    updateFormIndices() {
        const forms = this.formsetContainer.querySelectorAll(`.${this.formClass}`);
        let formIndex = 0;

        forms.forEach(form => {
            if (form.style.display === 'none') return;

            // Update all input, select, and textarea elements
            form.querySelectorAll('input, select, textarea').forEach(field => {
                if (field.name) {
                    // Replace the form index in the name attribute
                    field.name = field.name.replace(
                        new RegExp(`${this.prefix}-(\\d+)-`),
                        `${this.prefix}-${formIndex}-`
                    );
                }
                if (field.id) {
                    // Replace the form index in the id attribute
                    field.id = field.id.replace(
                        new RegExp(`id_${this.prefix}-(\\d+)-`),
                        `id_${this.prefix}-${formIndex}-`
                    );
                }
            });

            // Update labels
            form.querySelectorAll('label').forEach(label => {
                if (label.htmlFor) {
                    label.htmlFor = label.htmlFor.replace(
                        new RegExp(`id_${this.prefix}-(\\d+)-`),
                        `id_${this.prefix}-${formIndex}-`
                    );
                }
            });

            formIndex++;
        });

        // Update TOTAL_FORMS
        this.managementForm.totalForms.value = formIndex;
    }

    updateOrderFields() {
        const forms = this.formsetContainer.querySelectorAll(`.${this.formClass}`);
        let order = 1;

        forms.forEach(form => {
            if (form.style.display === 'none') return;

            const orderField = form.querySelector(`input[name$="-order"]`);
            if (orderField) {
                orderField.value = order;
            }

            // Update step numbers if this is a step formset
            const stepNumber = form.querySelector('.step-number');
            if (stepNumber) {
                stepNumber.textContent = order;
            }

            order++;
        });
    }

    enableDragAndDrop() {
        const forms = this.formsetContainer.querySelectorAll(`.${this.formClass}`);

        forms.forEach(form => {
            form.setAttribute('draggable', 'true');

            form.addEventListener('dragstart', (e) => {
                form.classList.add('dragging');
                e.dataTransfer.effectAllowed = 'move';
            });

            form.addEventListener('dragend', (e) => {
                form.classList.remove('dragging');
            });

            form.addEventListener('dragover', (e) => {
                e.preventDefault();
                const dragging = this.formsetContainer.querySelector('.dragging');
                const afterElement = this.getDragAfterElement(e.clientY);

                if (afterElement == null) {
                    this.formsetContainer.appendChild(dragging);
                } else {
                    this.formsetContainer.insertBefore(dragging, afterElement);
                }
            });

            form.addEventListener('drop', (e) => {
                e.preventDefault();
                this.updateOrderFields();
            });
        });
    }

    getDragAfterElement(y) {
        const draggableElements = [...this.formsetContainer.querySelectorAll(`.${this.formClass}:not(.dragging)`)];

        return draggableElements.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;

            if (offset < 0 && offset > closest.offset) {
                return { offset: offset, element: child };
            } else {
                return closest;
            }
        }, { offset: Number.NEGATIVE_INFINITY }).element;
    }
}
