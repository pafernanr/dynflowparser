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
      const header = node.querySelector('.action-header');
      const details = node.querySelector('.action-details');

      if (header && details) {
        header.addEventListener('click', (e) => {
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
      const header = node.querySelector('.step-header');
      const details = node.querySelector('.step-details');

      if (header && details) {
        header.addEventListener('click', (e) => {
          if (e.target.tagName === 'A' || e.target.tagName === 'BUTTON') {
            return;
          }

          details.classList.toggle('expanded');
          header.classList.toggle('expanded');
        });
      }
    });

    // Initialize tabs
    initTabs();

    // Auto-expand errors on actions page
    if (document.querySelector('.action-tree')) {
      setTimeout(expandErrors, 100);
    }
  }

  /**
   * Initialize tab functionality
   */
  function initTabs() {
    const tabContainers = document.querySelectorAll('.tabs-container');

    tabContainers.forEach(container => {
      const tabs = container.querySelectorAll('.tab');
      const contents = container.parentElement.querySelectorAll('.tab-content');

      tabs.forEach((tab, index) => {
        tab.addEventListener('click', () => {
          // Remove active class from all tabs and contents
          tabs.forEach(t => t.classList.remove('active'));
          contents.forEach(c => c.classList.remove('active'));

          // Add active class to clicked tab and corresponding content
          tab.classList.add('active');
          if (contents[index]) {
            contents[index].classList.add('active');
          }
        });
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
