package org.matsim.project;

import org.matsim.api.core.v01.network.Network;
import org.matsim.api.core.v01.network.NetworkWriter;
import org.matsim.contrib.osm.networkReader.SupersonicOsmNetworkReader;
import org.matsim.core.network.NetworkUtils;
import org.matsim.core.network.algorithms.NetworkCleaner;
import org.matsim.core.utils.geometry.CoordinateTransformation;
import org.matsim.core.utils.geometry.transformations.TransformationFactory;
import org.matsim.core.utils.io.OsmNetworkReader;

import java.nio.file.Files;
import java.nio.file.Path;

public class PrepareShamalganNetwork {

	public static void main(String[] args) {
		if (args.length < 2) {
			System.out.println("Usage:");
			System.out.println("  PrepareShamalganNetwork <input.osm/.osm.pbf> <output-network.xml> [targetCrs]");
			System.out.println("Example:");
			System.out.println("  PrepareShamalganNetwork original-input-data/shamalgan/Shamalgan.osm scenarios/shamalgan/network.xml EPSG:32643");
			return;
		}

		String inputOsm = args[0];
		String outputNetwork = args[1];
		String targetCrs = args.length >= 3 ? args[2] : "EPSG:32643";

		Path inputPath = Path.of(inputOsm);
		if (!Files.exists(inputPath)) {
			throw new IllegalArgumentException("OSM file not found: " + inputPath.toAbsolutePath());
		}

		Path outputPath = Path.of(outputNetwork);
		try {
			if (outputPath.getParent() != null) {
				Files.createDirectories(outputPath.getParent());
			}
		} catch (Exception e) {
			throw new RuntimeException("Cannot create output directory for: " + outputPath.toAbsolutePath(), e);
		}

		CoordinateTransformation transformation =
				TransformationFactory.getCoordinateTransformation(TransformationFactory.WGS84, targetCrs);

		String lowerName = inputPath.getFileName().toString().toLowerCase();
		Network network;
		if (lowerName.endsWith(".pbf")) {
			network = new SupersonicOsmNetworkReader.Builder()
					.setCoordinateTransformation(transformation)
					.build()
					.read(inputOsm);
		} else {
			// Fallback for .osm/.osm.gz XML sources.
			network = NetworkUtils.createNetwork();
			new OsmNetworkReader(network, transformation).parse(inputOsm);
		}

		new NetworkCleaner().run(network);
		new NetworkWriter(network).write(outputPath.toString());

		System.out.println("Network created: " + outputPath.toAbsolutePath());
	}
}
