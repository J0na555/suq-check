/** Price history as a filled line. Flat series still draw a centred line. */

import { useMemo } from 'react';
import { View } from 'react-native';
import Svg, { Circle, Line, Path } from 'react-native-svg';

import { colors } from '../theme/tokens';

type Props = {
  values: number[];
  width: number;
  height?: number;
  color?: string;
};

export function Sparkline({ values, width, height = 64, color = colors.brand }: Props) {
  const geometry = useMemo(() => {
    if (values.length < 2) return null;

    const inset = 4;
    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = max - min || 1;
    const stepX = (width - inset * 2) / (values.length - 1);

    const points = values.map((value, index) => ({
      x: inset + index * stepX,
      y: inset + (1 - (value - min) / span) * (height - inset * 2),
    }));

    const line = points
      .map((point, index) => `${index === 0 ? 'M' : 'L'}${point.x} ${point.y}`)
      .join(' ');
    const area = `${line} L${points[points.length - 1].x} ${height} L${points[0].x} ${height} Z`;

    return { line, area, last: points[points.length - 1] };
  }, [values, width, height]);

  if (!geometry) return <View style={{ width, height }} />;

  return (
    <Svg width={width} height={height}>
      {[0.25, 0.5, 0.75].map((ratio) => (
        <Line
          key={ratio}
          x1={0}
          x2={width}
          y1={height * ratio}
          y2={height * ratio}
          stroke={colors.chartGrid}
          strokeDasharray="4 4"
        />
      ))}
      <Path d={geometry.area} fill={color} fillOpacity={0.12} />
      <Path d={geometry.line} stroke={color} strokeWidth={2.5} fill="none" strokeLinejoin="round" />
      <Circle cx={geometry.last.x} cy={geometry.last.y} r={3.5} fill={color} />
    </Svg>
  );
}
