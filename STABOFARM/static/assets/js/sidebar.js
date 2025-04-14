
// Toggle the visibility of a dropdown menu
const toggleDropdown = (dropdown, menu, isOpen) => {
  dropdown.classList.toggle("open", isOpen);
  menu.style.height = isOpen ? `${menu.scrollHeight}px` : 0;
};
// Close all open dropdowns
const closeAllDropdowns = () => {
  document.querySelectorAll(".dropdown-container.open").forEach((openDropdown) => {
    toggleDropdown(openDropdown, openDropdown.querySelector(".dropdown-menu"), false);
  });
};
// Attach click event to all dropdown toggles
document.querySelectorAll(".dropdown-toggle").forEach((dropdownToggle) => {
  dropdownToggle.addEventListener("click", (e) => {
    e.preventDefault();
    const dropdown = dropdownToggle.closest(".dropdown-container");
    const menu = dropdown.querySelector(".dropdown-menu");
    const isOpen = dropdown.classList.contains("open");
    closeAllDropdowns(); // Close all open dropdowns
    toggleDropdown(dropdown, menu, !isOpen); // Toggle current dropdown visibility
  });
});
// Attach click event to sidebar toggle buttons
document.querySelectorAll(".sidebar-toggler, .sidebar-menu-button").forEach((button) => {
  button.addEventListener("click", () => {
    closeAllDropdowns(); // Close all open dropdowns
    document.querySelector(".sidebar").classList.toggle("collapsed"); // Toggle collapsed class on sidebar
  });
});
// Collapse sidebar by default on small screens
if (window.innerWidth <= 1024) document.querySelector(".sidebar").classList.add("collapsed");




// form.js
document.addEventListener('DOMContentLoaded', function() {
  // Image Preview
  const imageInput = document.getElementById('id_image');
  const previewContainer = document.getElementById('imagePreview');

  if(imageInput && previewContainer) {
      imageInput.addEventListener('change', function() {
          const file = this.files[0];
          if(file) {
              const reader = new FileReader();
              reader.onload = function(e) {
                  previewContainer.innerHTML = `
                      <img src="${e.target.result}" 
                           class="image-preview" 
                           alt="Image preview"
                           style="max-width: 100%; height: auto;">`;
              }
              reader.readAsDataURL(file);
          }
      });
  }

  // Dynamic Variation Management
  const variationContainer = document.getElementById('variationContainer');
  const addVariationBtn = document.getElementById('addVariation');

  if(addVariationBtn && variationContainer) {
      addVariationBtn.addEventListener('click', function(e) {
          e.preventDefault();
          const newVariation = document.createElement('div');
          newVariation.classList.add('variation-group');
          newVariation.innerHTML = `
              <select name="variation_category" required>
                  <option value="">Select Category</option>
                  {% for cat in variation_categories %}
                  <option value="{{ cat.id }}">{{ cat.name }}</option>
                  {% endfor %}
              </select>
              <input type="text" name="variation_value" placeholder="Value" required>
              <button class="remove-variation" type="button">
                  <span class="material-symbols-rounded">close</span>
              </button>
          `;
          variationContainer.appendChild(newVariation);
      });
  }

  // Remove Variation
  document.addEventListener('click', function(e) {
      if(e.target.closest('.remove-variation')) {
          e.target.closest('.variation-group').remove();
      }
  });

  // Form Validation
  const forms = document.querySelectorAll('form');
  forms.forEach(form => {
      form.addEventListener('submit', function(e) {
          let valid = true;
          form.querySelectorAll('[required]').forEach(input => {
              if(!input.value.trim()) {
                  valid = false;
                  input.classList.add('error');
              } else {
                  input.classList.remove('error');
              }
          });
          
          if(!valid) {
              e.preventDefault();
              alert('Please fill all required fields');
          }
      });
  });
});



// category_form.js
document.addEventListener('DOMContentLoaded', function() {
  const categorySearch = document.getElementById('categorySearch');
  const suggestionsContainer = document.querySelector('.suggestions-container');
  const newCategoryInput = document.querySelector('#id_new_category');
  const categoryNameInput = document.querySelector('#id_category_name');
  const parentInput = document.querySelector('#id_parent');
  let timeout = null;

  // Fetch category suggestions
  const fetchSuggestions = async (query) => {
      const response = await fetch(`/api/categories/?search=${encodeURIComponent(query)}`);
      return await response.json();
  };

  // Handle category input
  categorySearch.addEventListener('input', function(e) {
      clearTimeout(timeout);
      const query = e.target.value.trim();
      
      timeout = setTimeout(async () => {
          if(query.length > 0) {
              const suggestions = await fetchSuggestions(query);
              showSuggestions(suggestions, query);
          } else {
              suggestionsContainer.innerHTML = '';
          }
      }, 300);
  });

  // Show suggestions dropdown
  const showSuggestions = (suggestions, query) => {
      let html = '';
      
      if(suggestions.length > 0) {
          html += suggestions.map(cat => `
              <div class="suggestion-item" 
                   data-id="${cat.id}"
                   data-parent="${cat.parent ? cat.parent.id : ''}">
                  ${cat.category_name}
                  ${cat.parent ? `<span class="parent-category">› ${cat.parent.category_name}</span>` : ''}
              </div>
          `).join('');
      }
      
      html += `
          <div class="suggestion-item new-category">
              Create new: "${query}"
          </div>
      `;

      suggestionsContainer.innerHTML = html;
      suggestionsContainer.classList.add('active');
  };

  // Handle suggestion selection
  suggestionsContainer.addEventListener('click', function(e) {
      const item = e.target.closest('.suggestion-item');
      if(!item) return;

      if(item.classList.contains('new-category')) {
          categorySearch.value = '';
          newCategoryInput.value = categorySearch.value;
          categoryNameInput.value = '';
          parentInput.value = '';
      } else {
          const categoryId = item.dataset.id;
          const categoryName = item.textContent.split('›')[0].trim();
          const parentId = item.dataset.parent || '';
          
          categorySearch.value = categoryName;
          categoryNameInput.value = categoryId;
          parentInput.value = parentId;
          newCategoryInput.value = '';
      }
      
      suggestionsContainer.classList.remove('active');
  });

  // Close dropdown when clicking outside
  document.addEventListener('click', function(e) {
      if(!e.target.closest('.combo-box')) {
          suggestionsContainer.classList.remove('active');
      }
  });
});


// variation_form.js
document.addEventListener('DOMContentLoaded', function() {
  const modal = document.getElementById('categoryModal');
  const addBtn = document.getElementById('addCategoryBtn');
  const closeBtn = document.querySelector('.close');
  const categorySelect = document.getElementById('id_category');

  // Open modal
  addBtn.addEventListener('click', () => modal.style.display = 'block');

  // Close modal
  closeBtn.addEventListener('click', () => modal.style.display = 'none');

  // Handle new category submission
  document.getElementById('newCategoryForm').addEventListener('submit', function(e) {
      e.preventDefault();
      const formData = new FormData(this);
      
      fetch('{% url "variation_category_create" %}', {
          method: 'POST',
          headers: {
              'X-Requested-With': 'XMLHttpRequest',
              'X-CSRFToken': '{{ csrf_token }}'
          },
          body: formData
      })
      .then(response => response.json())
      .then(data => {
          const newOption = new Option(data.name, data.id);
          categorySelect.add(newOption);
          newOption.selected = true;
          modal.style.display = 'none';
          this.reset();
      });
  });
});


document.addEventListener('DOMContentLoaded', function() {
  const tabs = document.querySelectorAll('.tab');
  const contents = document.querySelectorAll('.tab-content');

  tabs.forEach(tab => {
      tab.addEventListener('click', function() {
          const target = document.getElementById(this.dataset.target);
          
          // Remove active classes
          tabs.forEach(t => t.classList.remove('active'));
          contents.forEach(c => c.classList.remove('active'));
          
          // Add active classes
          this.classList.add('active');
          target.classList.add('active');
      });
  });
});

document.querySelectorAll('.thumbnail').forEach(thumb => {
  thumb.addEventListener('click', function() {
      const mainImg = document.querySelector('.main-image img');
      mainImg.src = this.src;
  });
});