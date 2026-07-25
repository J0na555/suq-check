/** The confidence score, drawn as an arc so the band is readable at a glance. */

import { StyleSheet, Text, View } from 'react-native';
import Svg, { Circle } from 'react-native-svg';

import { bandPalette, colors, type ConfidenceBand } from '../theme/tokens';

type Props = {
  score: number;
  band: ConfidenceBand;
  size?: number;
  caption?: string;
};

export function ConfidenceRing({ score, band, size = 96, caption = 'out of 100' }: Props) {
  const stroke = Math.max(size * 0.09, 6);
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const filled = circumference * Math.min(Math.max(score, 0), 100) / 100;
  const palette = bandPalette[band];

  return (
    <View style={{ width: size, height: size }}>
      <Svg width={size} height={size}>
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={colors.surfaceMuted}
          strokeWidth={stroke}
          fill="none"
        />
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={palette.fg}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${filled} ${circumference - filled}`}
          // Start the arc at twelve o'clock instead of three.
          rotation={-90}
          originX={size / 2}
          originY={size / 2}
          fill="none"
        />
      </Svg>
      <View style={styles.center} pointerEvents="none">
        <Text style={[styles.score, { color: palette.fg, fontSize: size * 0.3 }]}>{score}</Text>
        <Text style={styles.caption}>{caption}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  center: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    alignItems: 'center',
    justifyContent: 'center',
  },
  score: {
    fontWeight: '700',
  },
  caption: {
    color: colors.textFaint,
    fontSize: 10,
  },
});
