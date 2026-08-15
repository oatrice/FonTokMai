import '@testing-library/jest-dom';

// Mock d3-geo for Jest test environment
jest.mock('d3-geo', () => ({
  geoMercator: () => {
    const fn: any = (coords: [number, number]) => [
      ((coords[0] - 97) / (106 - 97)) * 520,
      ((20.5 - coords[1]) / (20.5 - 5.5)) * 780,
    ];
    fn.fitExtent = () => fn;
    return fn;
  },
  geoPath: () => () => 'M 0 0 L 10 10',
}));
