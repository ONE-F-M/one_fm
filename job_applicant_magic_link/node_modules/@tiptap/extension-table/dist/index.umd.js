(function (global, factory) {
  typeof exports === 'object' && typeof module !== 'undefined' ? factory(exports, require('@tiptap/core'), require('@tiptap/pm/state'), require('@tiptap/pm/tables')) :
  typeof define === 'function' && define.amd ? define(['exports', '@tiptap/core', '@tiptap/pm/state', '@tiptap/pm/tables'], factory) :
  (global = typeof globalThis !== 'undefined' ? globalThis : global || self, factory(global["@tiptap/extension-table"] = {}, global.core, global.state, global.tables));
})(this, (function (exports, core, state, tables) { 'use strict';

  function updateColumns(node, colgroup, table, cellMinWidth, overrideCol, overrideValue) {
      let totalWidth = 0;
      let fixedWidth = true;
      let nextDOM = colgroup.firstChild;
      const row = node.firstChild;
      for (let i = 0, col = 0; i < row.childCount; i += 1) {
          const { colspan, colwidth } = row.child(i).attrs;
          for (let j = 0; j < colspan; j += 1, col += 1) {
              const hasWidth = overrideCol === col ? overrideValue : colwidth && colwidth[j];
              const cssWidth = hasWidth ? `${hasWidth}px` : '';
              totalWidth += hasWidth || cellMinWidth;
              if (!hasWidth) {
                  fixedWidth = false;
              }
              if (!nextDOM) {
                  colgroup.appendChild(document.createElement('col')).style.width = cssWidth;
              }
              else {
                  if (nextDOM.style.width !== cssWidth) {
                      nextDOM.style.width = cssWidth;
                  }
                  nextDOM = nextDOM.nextSibling;
              }
          }
      }
      while (nextDOM) {
          const after = nextDOM.nextSibling;
          nextDOM.parentNode.removeChild(nextDOM);
          nextDOM = after;
      }
      if (fixedWidth) {
          table.style.width = `${totalWidth}px`;
          table.style.minWidth = '';
      }
      else {
          table.style.width = '';
          table.style.minWidth = `${totalWidth}px`;
      }
  }
  class TableView {
      constructor(node, cellMinWidth) {
          this.node = node;
          this.cellMinWidth = cellMinWidth;
          this.dom = document.createElement('div');
          this.dom.className = 'tableWrapper';
          this.table = this.dom.appendChild(document.createElement('table'));
          this.colgroup = this.table.appendChild(document.createElement('colgroup'));
          updateColumns(node, this.colgroup, this.table, cellMinWidth);
          this.contentDOM = this.table.appendChild(document.createElement('tbody'));
      }
      update(node) {
          if (node.type !== this.node.type) {
              return false;
          }
          this.node = node;
          updateColumns(node, this.colgroup, this.table, this.cellMinWidth);
          return true;
      }
      ignoreMutation(mutation) {
          return (mutation.type === 'attributes'
              && (mutation.target === this.table || this.colgroup.contains(mutation.target)));
      }
  }

  function createCell(cellType, cellContent) {
      if (cellContent) {
          return cellType.createChecked(null, cellContent);
      }
      return cellType.createAndFill();
  }

  function getTableNodeTypes(schema) {
      if (schema.cached.tableNodeTypes) {
          return schema.cached.tableNodeTypes;
      }
      const roles = {};
      Object.keys(schema.nodes).forEach(type => {
          const nodeType = schema.nodes[type];
          if (nodeType.spec.tableRole) {
              roles[nodeType.spec.tableRole] = nodeType;
          }
      });
      schema.cached.tableNodeTypes = roles;
      return roles;
  }

  function createTable(schema, rowsCount, colsCount, withHeaderRow, cellContent) {
      const types = getTableNodeTypes(schema);
      const headerCells = [];
      const cells = [];
      for (let index = 0; index < colsCount; index += 1) {
          const cell = createCell(types.cell, cellContent);
          if (cell) {
              cells.push(cell);
          }
          if (withHeaderRow) {
              const headerCell = createCell(types.header_cell, cellContent);
              if (headerCell) {
                  headerCells.push(headerCell);
              }
          }
      }
      const rows = [];
      for (let index = 0; index < rowsCount; index += 1) {
          rows.push(types.row.createChecked(null, withHeaderRow && index === 0 ? headerCells : cells));
      }
      return types.table.createChecked(null, rows);
  }

  function isCellSelection(value) {
      return value instanceof tables.CellSelection;
  }

  const deleteTableWhenAllCellsSelected = ({ editor }) => {
      const { selection } = editor.state;
      if (!isCellSelection(selection)) {
          return false;
      }
      let cellCount = 0;
      const table = core.findParentNodeClosestToPos(selection.ranges[0].$from, node => {
          return node.type.name === 'table';
      });
      table === null || table === void 0 ? void 0 : table.node.descendants(node => {
          if (node.type.name === 'table') {
              return false;
          }
          if (['tableCell', 'tableHeader'].includes(node.type.name)) {
              cellCount += 1;
          }
      });
      const allCellsSelected = cellCount === selection.ranges.length;
      if (!allCellsSelected) {
          return false;
      }
      editor.commands.deleteTable();
      return true;
  };

  const Table = core.Node.create({
      name: 'table',
      // @ts-ignore
      addOptions() {
          return {
              HTMLAttributes: {},
              resizable: false,
              handleWidth: 5,
              cellMinWidth: 25,
              // TODO: fix
              View: TableView,
              lastColumnResizable: true,
              allowTableNodeSelection: false,
          };
      },
      content: 'tableRow+',
      tableRole: 'table',
      isolating: true,
      group: 'block',
      parseHTML() {
          return [{ tag: 'table' }];
      },
      renderHTML({ HTMLAttributes }) {
          return ['table', core.mergeAttributes(this.options.HTMLAttributes, HTMLAttributes), ['tbody', 0]];
      },
      addCommands() {
          return {
              insertTable: ({ rows = 3, cols = 3, withHeaderRow = true } = {}) => ({ tr, dispatch, editor }) => {
                  const node = createTable(editor.schema, rows, cols, withHeaderRow);
                  if (dispatch) {
                      const offset = tr.selection.anchor + 1;
                      tr.replaceSelectionWith(node)
                          .scrollIntoView()
                          .setSelection(state.TextSelection.near(tr.doc.resolve(offset)));
                  }
                  return true;
              },
              addColumnBefore: () => ({ state, dispatch }) => {
                  return tables.addColumnBefore(state, dispatch);
              },
              addColumnAfter: () => ({ state, dispatch }) => {
                  return tables.addColumnAfter(state, dispatch);
              },
              deleteColumn: () => ({ state, dispatch }) => {
                  return tables.deleteColumn(state, dispatch);
              },
              addRowBefore: () => ({ state, dispatch }) => {
                  return tables.addRowBefore(state, dispatch);
              },
              addRowAfter: () => ({ state, dispatch }) => {
                  return tables.addRowAfter(state, dispatch);
              },
              deleteRow: () => ({ state, dispatch }) => {
                  return tables.deleteRow(state, dispatch);
              },
              deleteTable: () => ({ state, dispatch }) => {
                  return tables.deleteTable(state, dispatch);
              },
              mergeCells: () => ({ state, dispatch }) => {
                  return tables.mergeCells(state, dispatch);
              },
              splitCell: () => ({ state, dispatch }) => {
                  return tables.splitCell(state, dispatch);
              },
              toggleHeaderColumn: () => ({ state, dispatch }) => {
                  return tables.toggleHeader('column')(state, dispatch);
              },
              toggleHeaderRow: () => ({ state, dispatch }) => {
                  return tables.toggleHeader('row')(state, dispatch);
              },
              toggleHeaderCell: () => ({ state, dispatch }) => {
                  return tables.toggleHeaderCell(state, dispatch);
              },
              mergeOrSplit: () => ({ state, dispatch }) => {
                  if (tables.mergeCells(state, dispatch)) {
                      return true;
                  }
                  return tables.splitCell(state, dispatch);
              },
              setCellAttribute: (name, value) => ({ state, dispatch }) => {
                  return tables.setCellAttr(name, value)(state, dispatch);
              },
              goToNextCell: () => ({ state, dispatch }) => {
                  return tables.goToNextCell(1)(state, dispatch);
              },
              goToPreviousCell: () => ({ state, dispatch }) => {
                  return tables.goToNextCell(-1)(state, dispatch);
              },
              fixTables: () => ({ state, dispatch }) => {
                  if (dispatch) {
                      tables.fixTables(state);
                  }
                  return true;
              },
              setCellSelection: position => ({ tr, dispatch }) => {
                  if (dispatch) {
                      const selection = tables.CellSelection.create(tr.doc, position.anchorCell, position.headCell);
                      // @ts-ignore
                      tr.setSelection(selection);
                  }
                  return true;
              },
          };
      },
      addKeyboardShortcuts() {
          return {
              Tab: () => {
                  if (this.editor.commands.goToNextCell()) {
                      return true;
                  }
                  if (!this.editor.can().addRowAfter()) {
                      return false;
                  }
                  return this.editor.chain().addRowAfter().goToNextCell().run();
              },
              'Shift-Tab': () => this.editor.commands.goToPreviousCell(),
              Backspace: deleteTableWhenAllCellsSelected,
              'Mod-Backspace': deleteTableWhenAllCellsSelected,
              Delete: deleteTableWhenAllCellsSelected,
              'Mod-Delete': deleteTableWhenAllCellsSelected,
          };
      },
      addProseMirrorPlugins() {
          const isResizable = this.options.resizable && this.editor.isEditable;
          return [
              ...(isResizable
                  ? [
                      tables.columnResizing({
                          handleWidth: this.options.handleWidth,
                          cellMinWidth: this.options.cellMinWidth,
                          // @ts-ignore (incorrect type)
                          View: this.options.View,
                          // TODO: PR for @types/prosemirror-tables
                          // @ts-ignore (incorrect type)
                          lastColumnResizable: this.options.lastColumnResizable,
                      }),
                  ]
                  : []),
              tables.tableEditing({
                  allowTableNodeSelection: this.options.allowTableNodeSelection,
              }),
          ];
      },
      extendNodeSchema(extension) {
          const context = {
              name: extension.name,
              options: extension.options,
              storage: extension.storage,
          };
          return {
              tableRole: core.callOrReturn(core.getExtensionField(extension, 'tableRole', context)),
          };
      },
  });

  exports.Table = Table;
  exports.createTable = createTable;
  exports["default"] = Table;

  Object.defineProperty(exports, '__esModule', { value: true });

}));
//# sourceMappingURL=index.umd.js.map
