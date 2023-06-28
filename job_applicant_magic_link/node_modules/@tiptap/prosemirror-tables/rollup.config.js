import { babel } from '@rollup/plugin-babel';

import { name, main, umd, module } from './package.json';

console.log(main, umd, module);

export default {
  input: './src/index.js',
  output: [
    {
      name,
      file: main,
      format: 'cjs',
      sourcemap: true,
    },
    {
      name,
      file: umd,
      format: 'umd',
      sourcemap: true,
    },
    {
      name,
      file: module,
      format: 'es',
      sourcemap: true,
    },
  ],
  plugins: [babel({ babelHelpers: 'bundled' })],
  external(id) {
    return !/^[\.\/]/.test(id);
  },
};
