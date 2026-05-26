/**
 * Modern DynflowParserNG JavaScript
 * Vanilla JS implementation - no jQuery required
 */

(function() {
  'use strict';

  // Wait for DOM to be ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  function init() {
    initTaskList();
    initActionTree();
    initButtons();
    initHeaderCollapse();
  }

  /**
   * Initialize task list functionality
   */
  function initTaskList() {
    const taskItems = document.querySelectorAll('.task-item');

    taskItems.forEach(task => {
      const header = task.querySelector('.task-header');
      const children = task.querySelector('.task-children');

      if (header && children) {
        header.addEventListener('click', () => {
          children.classList.toggle('expanded');
          header.classList.toggle('expanded');
        });
      }
    });
  }

  /**
   * Initialize action tree functionality
   */
  function initActionTree() {
    // Initialize action nodes
    const actionNodes = document.querySelectorAll('.action-node');

    actionNodes.forEach(node => {
      const actionClass = node.querySelector('.action-class');
      const details = node.querySelector('.action-details');
      const header = node.querySelector('.action-header');

      if (actionClass && details && header) {
        actionClass.addEventListener('click', (e) => {
          // Don't toggle if clicking on a link or button
          if (e.target.tagName === 'A' || e.target.tagName === 'BUTTON') {
            return;
          }

          details.classList.toggle('expanded');
          header.classList.toggle('expanded');
        });
      }
    });

    // Initialize step nodes
    const stepNodes = document.querySelectorAll('.step-node');

    stepNodes.forEach(node => {
      const stepClass = node.querySelector('.step-class');
      const details = node.querySelector('.step-details');
      const header = node.querySelector('.step-header');

      if (stepClass && details && header) {
        stepClass.addEventListener('click', (e) => {
          if (e.target.tagName === 'A' || e.target.tagName === 'BUTTON') {
            return;
          }

          details.classList.toggle('expanded');
          header.classList.toggle('expanded');
        });
      }
    });

    // Initialize inline content buttons
    initContentButtons();

    // Auto-expand errors on actions page
    if (document.querySelector('.action-tree, .action-tree-scrollable')) {
      setTimeout(expandErrors, 100);
    }
  }

  /**
   * Initialize inline content button functionality
   */
  function initContentButtons() {
    const contentButtons = document.querySelectorAll('.btn-inline');

    contentButtons.forEach(button => {
      button.addEventListener('click', (e) => {
        e.stopPropagation(); // Don't trigger parent header click

        const targetId = button.getAttribute('data-target');
        const targetContent = document.getElementById(targetId);

        if (!targetContent) return;

        // Find the parent details container
        const detailsContainer = targetContent.parentElement;

        // Get all buttons in the same group
        const siblingButtons = button.parentElement.querySelectorAll('.btn-inline');

        // Get all content areas in the same details container
        const siblingContents = detailsContainer.querySelectorAll('.content-area');

        // If this content is already visible, hide it
        if (targetContent.classList.contains('visible')) {
          targetContent.classList.remove('visible');
          button.classList.remove('active');
        } else {
          // Hide all other contents and deactivate buttons
          siblingContents.forEach(c => c.classList.remove('visible'));
          siblingButtons.forEach(b => b.classList.remove('active'));

          // Show clicked content and activate button
          targetContent.classList.add('visible');
          button.classList.add('active');
        }
      });
    });
  }

  /**
   * Initialize control buttons
   */
  function initButtons() {
    // Expand All button
    const expandAllBtn = document.getElementById('expandAll');
    if (expandAllBtn) {
      expandAllBtn.addEventListener('click', expandAll);
    }

    // Collapse All button
    const collapseAllBtn = document.getElementById('collapseAll');
    if (collapseAllBtn) {
      collapseAllBtn.addEventListener('click', collapseAll);
    }

    // Expand Errors button
    const expandErrorsBtn = document.getElementById('expandErrors');
    if (expandErrorsBtn) {
      expandErrorsBtn.addEventListener('click', expandErrors);
    }
  }

  /**
   * Expand all action nodes
   */
  function expandAll() {
    document.querySelectorAll('.action-details').forEach(details => {
      details.classList.add('expanded');
      const header = details.previousElementSibling;
      if (header) {
        header.classList.add('expanded');
      }
    });

    document.querySelectorAll('.step-details').forEach(details => {
      details.classList.add('expanded');
      const header = details.previousElementSibling;
      if (header) {
        header.classList.add('expanded');
      }
    });
  }

  /**
   * Collapse all action nodes
   */
  function collapseAll() {
    document.querySelectorAll('.action-details').forEach(details => {
      details.classList.remove('expanded');
      const header = details.previousElementSibling;
      if (header) {
        header.classList.remove('expanded');
      }
    });

    document.querySelectorAll('.step-details').forEach(details => {
      details.classList.remove('expanded');
      const header = details.previousElementSibling;
      if (header) {
        header.classList.remove('expanded');
      }
    });

    // Hide all content areas and deactivate buttons
    document.querySelectorAll('.content-area').forEach(c => c.classList.remove('visible'));
    document.querySelectorAll('.btn-inline').forEach(b => b.classList.remove('active'));
  }

  /**
   * Expand only nodes with errors or warnings
   */
  function expandErrors() {
    // First collapse all
    collapseAll();

    // Find all error and warning status badges
    const errorNodes = document.querySelectorAll(
      '.status-error, .status-warning, .status-pending, .status-skipped, .status-suspended'
    );

    errorNodes.forEach(badge => {
      // Find the parent action or step node
      let node = badge.closest('.action-node, .step-node');

      if (node) {
        const details = node.querySelector('.action-details, .step-details');
        const header = node.querySelector('.action-header, .step-header');

        if (details && header) {
          details.classList.add('expanded');
          header.classList.add('expanded');
        }

        // Also expand parent action if this is a step
        if (node.classList.contains('step-node')) {
          const parentAction = node.closest('.action-node');
          if (parentAction) {
            const parentDetails = parentAction.querySelector('.action-details');
            const parentHeader = parentAction.querySelector('.action-header');
            if (parentDetails && parentHeader) {
              parentDetails.classList.add('expanded');
              parentHeader.classList.add('expanded');
            }
          }
        }
      }
    });
  }

  /**
   * Utility: Get all parent nodes
   */
  function getParentNodes(element, selector) {
    const parents = [];
    let current = element.parentElement;

    while (current) {
      if (current.matches(selector)) {
        parents.push(current);
      }
      current = current.parentElement;
    }

    return parents;
  }

  /**
   * Initialize header collapse functionality (both pages)
   */
  function initHeaderCollapse() {
    const header = document.getElementById('pageHeader');
    const toggleBtn = document.getElementById('headerToggle');
    const scrollableArea = document.querySelector('.action-tree-scrollable, .task-list-scrollable');

    if (!header || !toggleBtn || !scrollableArea) {
      return; // Header not present on this page
    }

    let scrollTimeout;
    let lastScrollTop = 0;

    // Toggle header manually
    toggleBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      header.classList.toggle('collapsed');
    });

    // Auto-collapse header on scroll down
    scrollableArea.addEventListener('scroll', () => {
      const scrollTop = scrollableArea.scrollTop;

      // Clear previous timeout
      clearTimeout(scrollTimeout);

      // Collapse when scrolling down past 50px
      if (scrollTop > 50 && scrollTop > lastScrollTop) {
        scrollTimeout = setTimeout(() => {
          header.classList.add('collapsed');
        }, 150);
      }

      lastScrollTop = scrollTop;
    });
  }

  /**
   * Utility: Toggle element visibility with animation
   */
  function toggleElement(element) {
    if (element.classList.contains('expanded')) {
      element.classList.remove('expanded');
    } else {
      element.classList.add('expanded');
    }
  }

})();
