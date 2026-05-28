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
          // Don't toggle if user is selecting text
          if (window.getSelection().toString().length > 0) {
            return;
          }
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
      const expandIcon = actionClass ? actionClass.querySelector('.expand-icon') : null;

      // Shared toggle function for both icon and action class clicks
      const toggleAction = () => {
        // Toggle steps and child actions
        const stepsLists = details.querySelectorAll(':scope > .steps-list');
        const childActions = details.querySelectorAll(':scope > .child-actions');

        stepsLists.forEach(list => list.classList.toggle('expanded'));
        childActions.forEach(child => child.classList.toggle('expanded'));

        // Toggle header and details (icon rotation handled by CSS)
        header.classList.toggle('expanded');
        details.classList.toggle('expanded');
      };

      if (expandIcon) {
        expandIcon.addEventListener('click', (e) => {
          e.stopPropagation();
          toggleAction();
        });
      }

      if (actionClass && details && header) {
        actionClass.addEventListener('click', (e) => {
          // Don't toggle if clicking on a link or button
          if (e.target.tagName === 'A' || e.target.tagName === 'BUTTON') {
            return;
          }

          // Don't toggle if user is selecting text
          if (window.getSelection().toString().length > 0) {
            return;
          }

          toggleAction();
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

          // Don't toggle if user is selecting text
          if (window.getSelection().toString().length > 0) {
            return;
          }

          details.classList.toggle('expanded');
          header.classList.toggle('expanded');
        });
      }
    });

    // Initialize inline content buttons
    initContentButtons();

    // Auto-expand errors on page load
    if (document.querySelector('.action-tree, .action-tree-scrollable')) {
      setTimeout(autoExpandErrors, 100);
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

        // Find the parent details container (action-details or step-details)
        const detailsContainer = targetContent.closest('.action-details, .step-details');

        if (detailsContainer) {
          // If the parent is not expanded, expand it first
          if (!detailsContainer.classList.contains('expanded')) {
            detailsContainer.classList.add('expanded');
            // Also expand the header
            const header = detailsContainer.previousElementSibling;
            if (header) {
              header.classList.add('expanded');
            }
          }
        }

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
    // Expand All button (actions page)
    const expandAllBtn = document.getElementById('expandAll');
    if (expandAllBtn) {
      expandAllBtn.addEventListener('click', expandAll);
    }

    // Collapse All button (actions page)
    const collapseAllBtn = document.getElementById('collapseAll');
    if (collapseAllBtn) {
      collapseAllBtn.addEventListener('click', collapseAll);
    }

    // Expand Errors button (actions page)
    const expandErrorsBtn = document.getElementById('expandErrors');
    if (expandErrorsBtn) {
      expandErrorsBtn.addEventListener('click', autoExpandErrors);
    }

    // Expand All Tasks button (tasks page)
    const expandAllTasksBtn = document.getElementById('expandAllTasks');
    if (expandAllTasksBtn) {
      expandAllTasksBtn.addEventListener('click', expandAllTasks);
    }

    // Collapse All Tasks button (tasks page)
    const collapseAllTasksBtn = document.getElementById('collapseAllTasks');
    if (collapseAllTasksBtn) {
      collapseAllTasksBtn.addEventListener('click', collapseAllTasks);
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
   * Auto-expand actions and steps with non-success status
   * Optimized: stops iterating up the tree when finding an already-expanded parent
   */
  function autoExpandErrors() {
    // Find all status badges that are NOT success
    const allStatusBadges = document.querySelectorAll('[class*="status-"]');
    const errorBadges = Array.from(allStatusBadges).filter(badge =>
      !badge.classList.contains('status-success')
    );

    errorBadges.forEach(badge => {
      // Find the parent action or step node
      const node = badge.closest('.action-node, .step-node');

      if (node) {
        // For actions with non-success status: expand it and all parents
        if (node.classList.contains('action-node')) {
          expandNodeAndParents(node);
        }

        // For steps with non-success status: expand all parent actions
        if (node.classList.contains('step-node')) {
          const parentAction = node.closest('.action-node');
          if (parentAction) {
            expandNodeAndParents(parentAction);
          }
        }
      }
    });
  }

  /**
   * Expand a node and all its parent action nodes up to the root
   * Stops when it finds a parent that's already expanded
   */
  function expandNodeAndParents(node) {
    let current = node;

    while (current && current.classList.contains('action-node')) {
      const details = current.querySelector(':scope > .action-details');
      const header = current.querySelector(':scope > .action-header');
      const stepsLists = details ? details.querySelectorAll(':scope > .steps-list') : [];
      const childActions = details ? details.querySelectorAll(':scope > .child-actions') : [];
      const expandIcon = current.querySelector(':scope > .action-header .expand-icon');

      // Check if already expanded - if so, stop iterating
      if (details && details.classList.contains('expanded')) {
        break;
      }

      // Expand this node
      if (details && header) {
        details.classList.add('expanded');
        header.classList.add('expanded');
        stepsLists.forEach(list => list.classList.add('expanded'));
        childActions.forEach(child => child.classList.add('expanded'));
      }

      // Move to parent action node
      current = current.parentElement ? current.parentElement.closest('.action-node') : null;
    }
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

    if (!header || !toggleBtn) {
      return; // Header not present on this page
    }

    // Toggle header manually
    toggleBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      header.classList.toggle('collapsed');
      toggleBtn.classList.toggle('collapsed');
    });

    // Auto-collapse header 1 second after page load
    setTimeout(() => {
      header.classList.add('collapsed');
      toggleBtn.classList.add('collapsed');
    }, 1000);
  }

  /**
   * Expand all task children
   */
  function expandAllTasks() {
    document.querySelectorAll('.task-children').forEach(children => {
      children.classList.add('expanded');
      const header = children.previousElementSibling;
      if (header && header.classList.contains('task-header')) {
        header.classList.add('expanded');
      }
    });
  }

  /**
   * Collapse all task children
   */
  function collapseAllTasks() {
    document.querySelectorAll('.task-children').forEach(children => {
      children.classList.remove('expanded');
      const header = children.previousElementSibling;
      if (header && header.classList.contains('task-header')) {
        header.classList.remove('expanded');
      }
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
