package quic

import (
	"github.com/lucas-clemente/quic-go/internal/flowcontrol"
	"github.com/lucas-clemente/quic-go/internal/protocol"
	. "github.com/onsi/ginkgo"
	. "github.com/onsi/gomega"
)

type mockFlowControlManager struct{}

func isParent(n, child *node) bool {
	for _, c := range n.children {
		if c.id == child.id {
			return true
		}
	}
	return false
}

func (f *mockFlowControlManager) NewStream(streamID protocol.StreamID, contributesToConnection bool) {
	panic("not yet implemented")
}
func (f *mockFlowControlManager) RemoveStream(streamID protocol.StreamID) {
	panic("not yet implemented")
}
func (f *mockFlowControlManager) ResetStream(streamID protocol.StreamID, byteOffset protocol.ByteCount) error {
	panic("not yet implemented")
}
func (f *mockFlowControlManager) UpdateHighestReceived(streamID protocol.StreamID, byteOffset protocol.ByteCount) error {
	panic("not yet implemented")
}
func (f *mockFlowControlManager) AddBytesRead(streamID protocol.StreamID, n protocol.ByteCount) error {
	panic("not yet implemented")
}
func (f *mockFlowControlManager) GetWindowUpdates(force bool) (res []flowcontrol.WindowUpdate) {
	panic("not yet implemented")
}
func (f *mockFlowControlManager) GetReceiveWindow(streamID protocol.StreamID) (protocol.ByteCount, error) {
	panic("not yet implemented")
}
func (f *mockFlowControlManager) AddBytesSent(streamID protocol.StreamID, n protocol.ByteCount) error {
	return nil
}
func (f *mockFlowControlManager) GetBytesSent(streamID protocol.StreamID) (protocol.ByteCount, error) {
	panic("not yet implemented")
}
func (f *mockFlowControlManager) AddBytesRetrans(streamID protocol.StreamID, n protocol.ByteCount) error {
	panic("not yet implemented")
}
func (f *mockFlowControlManager) GetBytesRetrans(streamID protocol.StreamID) (protocol.ByteCount, error) {
	panic("not yet implemented")
}
func (f *mockFlowControlManager) SendWindowSize(streamID protocol.StreamID) (protocol.ByteCount, error) {
	return protocol.MaxByteCount, nil
}
func (f *mockFlowControlManager) RemainingConnectionWindowSize() protocol.ByteCount {
	return protocol.MaxByteCount
}
func (f *mockFlowControlManager) UpdateWindow(streamID protocol.StreamID, offset protocol.ByteCount) (bool, error) {
	panic("not yet implemented")
}

var _ = Describe("Stream Tree", func() {
	var (
		streamTree                         *streamTree
		cryptoStream, headerStream         *stream
		stream1, stream2, stream3, stream4 *stream
	)

	const (
		cryptoID = protocol.StreamID(1)
		headerID = protocol.StreamID(3)
		id1      = protocol.StreamID(4)
		id2      = protocol.StreamID(5)
		id3      = protocol.StreamID(6)
		id4      = protocol.StreamID(7)
	)

	BeforeEach(func() {
		streamTree = newStreamTree()
		cryptoStream = &stream{streamID: 1}
		headerStream = &stream{streamID: headerID}
		stream1 = &stream{streamID: id1}
		stream2 = &stream{streamID: id2}
		stream3 = &stream{streamID: id3}
		stream4 = &stream{streamID: id4}

		mockFcm := &mockFlowControlManager{}
		streamFramer := newStreamFramerTree(nil, mockFcm, streamTree)
		streamTree.streamFramer = streamFramer
	})

	Context("adding header stream node to dependency tree", func() {
		PIt("sets sch.root to header stream", func() {
			streamTree.addNode(headerStream)
			Expect(streamTree.root.stream).To(Equal(headerStream))
			Expect(streamTree.root.id).NotTo(Equal(headerStream.streamID))
		})

		It("sets header node active", func() {
			streamTree.addNode(headerStream)
			Expect(streamTree.root.state).To(Equal(nodeActive))
		})
	})

	Context("adding node to dependency tree", func() {
		It("adds node to nodeMap", func() {
			streamTree.addNode(stream1)
			Expect(len(streamTree.nodeMap)).To(Equal(1))
			streamTree.addNode(stream2)
			Expect(len(streamTree.nodeMap)).To(Equal(2))
			Expect(streamTree.nodeMap[id1].stream).To(Equal(stream1))
			Expect(streamTree.nodeMap[id2].stream).To(Equal(stream2))
			Expect(streamTree.nodeMap[id3]).To(BeNil())
		})

		It("adds sets root as its parent", func() {
			streamTree.addNode(stream1)
			Expect(streamTree.nodeMap[id1].parent).To(Equal(streamTree.root))
		})

		It("has root as parent", func() {
			streamTree.addNode(stream1)
			streamTree.setActive(id1)
			Expect(isParent(streamTree.root, streamTree.nodeMap[id1])).To(BeTrue())
		})

		It("is idle", func() {
			streamTree.addNode(stream1)
			Expect(streamTree.nodeMap[id1].state).To(Equal(nodeIdle))
		})

		It("has default weight", func() {
			streamTree.addNode(stream1)
			Expect(streamTree.nodeMap[id1].weight).To(Equal(protocol.DefaultStreamWeight))
		})

		It("is added to parents priority queue", func() {
			streamTree.addNode(stream1)
			streamTree.setActive(id1)
			Expect(len(streamTree.root.children)).To(Equal(1))
			Expect(streamTree.root.children[0]).To(Equal(streamTree.nodeMap[id1]))
		})

		It("does not add nil node", func() {
			err := streamTree.addNode(nil)
			Expect(err).To(HaveOccurred())
			Expect(len(streamTree.nodeMap)).To(Equal(0))
		})

		It("does add crypto stream", func() {
			err := streamTree.addNode(cryptoStream)
			Expect(err).ToNot(HaveOccurred())
			_, ok := streamTree.nodeMap[cryptoID]
			Expect(ok).To(Equal(true))
			Expect(len(streamTree.nodeMap)).To(Equal(1))
		})
	})

	Context("setting weight", func() {
		It("sets a new weight on existing nodes", func() {
			streamTree.addNode(stream1)
			err := streamTree.maybeSetWeight(id1, 255)
			Expect(err).ToNot(HaveOccurred())
			Expect(streamTree.nodeMap[id1].weight).To(Equal(uint8(255)))
			err = streamTree.maybeSetWeight(id2, 255)
			Expect(err).To(HaveOccurred())
		})

		It("does not set weight of crypto stream", func() {
			Expect(streamTree.maybeSetWeight(cryptoID, 255)).To(BeNil())
		})

		It("does not set weight of header stream", func() {
			streamTree.addNode(headerStream)
			Expect(streamTree.maybeSetWeight(headerID, 255)).To(BeNil())
			Expect(streamTree.root.weight).To(Equal(protocol.DefaultStreamWeight))
		})

		It("sets the childrens weight of the parent", func() {
			streamTree.addNode(headerStream)
			streamTree.addNode(stream1)
			streamTree.addNode(stream2)
			streamTree.setActive(id1)
			streamTree.setActive(id2)

			w1 := uint8(3)
			w2 := uint8(9)

			streamTree.maybeSetWeight(id1, w1)
			streamTree.maybeSetWeight(id2, w2)

			// childrensWeight adds 1 to the weight of each child
			Expect(streamTree.root.childrensWeight).To(Equal(uint32(w1 + w2 + 2)))
		})
	})

	Context("setting non-exclusive parent", func() {
		It("sets parent to a sibling", func() {
			//
			//		                    root
			//		root                  |
			//      /  \       -->        1
			//     1    2                 |
			//                            2
			//
			streamTree.addNode(headerStream)
			streamTree.addNode(stream1)
			streamTree.addNode(stream2)
			streamTree.setActive(id1)
			streamTree.setActive(id2)

			n1 := streamTree.nodeMap[id1]
			n2 := streamTree.nodeMap[id2]

			Expect(n1.parent).To(Equal(streamTree.root))
			Expect(n2.parent).To(Equal(streamTree.root))
			Expect(isParent(streamTree.root, n1)).To(BeTrue())
			Expect(isParent(streamTree.root, n2)).To(BeTrue())
			Expect(isParent(n1, n2)).To(BeFalse())
			Expect(len(streamTree.root.children)).To(Equal(2))

			err := streamTree.maybeSetParent(id2, id1, false)
			Expect(err).NotTo(HaveOccurred())
			Expect(n2.parent).To(Equal(n1))
			Expect(isParent(n1, n2)).To(BeTrue())
			Expect(n1.parent).To(Equal(streamTree.root))
			Expect(isParent(streamTree.root, n1)).To(BeTrue())
			Expect(isParent(streamTree.root, n2)).To(BeFalse())

			Expect(len(streamTree.root.children)).To(Equal(1))
			Expect(streamTree.root.children[0]).To(Equal(n1))
			Expect(len(n1.children)).To(Equal(1))
			Expect(n1.children[0]).To(Equal(n2))
		})

		It("sets parent to a previous descendant", func() {
			//
			//		                    root 0
			//		root                  |
			//       |          -->       3  6
			//       1                    |
			//       |                    1  4
			//       2                    |
			//      / \                   2  5
			//     3   4                  |
			//                            4  7
			//
			// Set up dependencies
			streamTree.addNode(headerStream)
			streamTree.addNode(stream1)
			streamTree.addNode(stream2)
			streamTree.addNode(stream3)
			streamTree.addNode(stream4)
			streamTree.setActive(id3)
			streamTree.setActive(id4)

			n1 := streamTree.nodeMap[id1]
			n2 := streamTree.nodeMap[id2]
			n3 := streamTree.nodeMap[id3]
			//n4 := streamTree.nodeMap[id4]

			err := streamTree.maybeSetParent(id2, id1, false)
			Expect(err).NotTo(HaveOccurred())
			err = streamTree.maybeSetParent(id3, id2, false)
			Expect(err).NotTo(HaveOccurred())
			err = streamTree.maybeSetParent(id4, id2, false)
			Expect(err).NotTo(HaveOccurred())

			// Set new parent of n1 to n3
			err = streamTree.maybeSetParent(id1, id3, false)
			Expect(err).NotTo(HaveOccurred())

			// Check if n3 has been updated correctly
			Expect(n3.parent).To(Equal(streamTree.root))
			Expect(n1.parent).To(Equal(n3))
			Expect(len(n3.children)).To(Equal(1))

			// Check if root has been updated correctly
			Expect(isParent(streamTree.root, n3)).To(BeTrue())
			Expect(isParent(streamTree.root, n1)).To(BeFalse())
			Expect(len(streamTree.root.children)).To(Equal(1))

			// Check if (remaining) child of n1 remains unchanged
			Expect(n2.parent).To(Equal(n1))
			Expect(isParent(n1, n2)).To(BeTrue())
			Expect(len(n1.children)).To(Equal(1))
		})

		// TODO: does not set self as parent
		It("does not set illegal parents", func() {
			streamTree.addNode(cryptoStream)
			streamTree.addNode(headerStream)
			streamTree.addNode(stream1)
			n1 := streamTree.nodeMap[id1]

			// Setting self as parent
			err := streamTree.maybeSetParent(id1, id1, false)
			Expect(err).To(HaveOccurred())
			Expect(n1.parent).To(Equal(streamTree.root))

			// Setting crypto stream as parent
			err = streamTree.maybeSetParent(id1, cryptoID, false)
			Expect(err).To(HaveOccurred())
			Expect(n1.parent).To(Equal(streamTree.root))

			// Setting unknown stream as parent
			err = streamTree.maybeSetParent(id1, id2, false)
			Expect(err).To(HaveOccurred())
			Expect(n1.parent).To(Equal(streamTree.root))

			// Setting parent of unknown stream
			err = streamTree.maybeSetParent(id2, id1, false)
			Expect(err).To(HaveOccurred())
			Expect(n1.parent).To(Equal(streamTree.root))

			// Setting parent of crypto stream
			err = streamTree.maybeSetParent(cryptoID, id1, false)
			Expect(err).To(HaveOccurred())

			// Setting parent of header stream
			err = streamTree.maybeSetParent(headerID, id1, false)
			Expect(err).To(HaveOccurred())
		})
	})

	Context("setting exclusivity", func() {

		It("sets exclusivity (same parent)", func() {
			//
			//		                    root
			//	   root                   |
			//       |         -->        1
			//       1                    |
			//      / \                   2
			//     2   3                  |
			//                            3
			//
			streamTree.addNode(headerStream)
			streamTree.addNode(stream1)
			streamTree.addNode(stream2)
			streamTree.setActive(id2)
			streamTree.addNode(stream3)
			streamTree.setActive(id3)
			n1 := streamTree.nodeMap[id1]
			n2 := streamTree.nodeMap[id2]
			n3 := streamTree.nodeMap[id3]
			err := streamTree.maybeSetParent(id2, id1, false)
			Expect(err).NotTo(HaveOccurred())
			err = streamTree.maybeSetParent(id3, id1, false)
			Expect(err).NotTo(HaveOccurred())

			err = streamTree.maybeSetParent(id2, id1, true)
			Expect(err).NotTo(HaveOccurred())

			Expect(n1.parent).To(Equal(streamTree.root))
			Expect(isParent(streamTree.root, n1)).To(BeTrue())
			Expect(len(streamTree.root.children)).To(Equal(1))

			Expect(n2.parent).To(Equal(n1))
			Expect(isParent(n1, n2)).To(BeTrue())
			Expect(len(n1.children)).To(Equal(1))

			Expect(n3.parent).To(Equal(n2))
			Expect(isParent(n2, n3)).To(BeTrue())
			Expect(len(n2.children)).To(Equal(1))
		})

		It("sets parent to a sibling (without children)", func() {
			//
			//		                    root
			//		root                  |
			//      /  \         -->      2
			//     1    2                 |
			//                            1
			//
			streamTree.addNode(headerStream)
			streamTree.addNode(stream1)
			streamTree.setActive(id1)
			streamTree.addNode(stream2)
			streamTree.setActive(id2)
			n1 := streamTree.nodeMap[id1]
			n2 := streamTree.nodeMap[id2]

			err := streamTree.maybeSetParent(id1, id2, true)
			Expect(err).NotTo(HaveOccurred())
			Expect(n1.parent).To(Equal(n2))
			Expect(isParent(n2, n1)).To(BeTrue())
			Expect(isParent(streamTree.root, n2)).To(BeTrue())
			Expect(len(streamTree.root.children)).To(Equal(1))
			Expect(len(n2.children)).To(Equal(1))
		})

		It("sets parent to a sibling (with children)", func() {
			//
			//		root                root
			//		/  \                  |
			//     1    2        -->      2
			//         / \                |
			//        3   4               1
			//                           / \
			//                          3   4
			//
			streamTree.addNode(headerStream)
			streamTree.addNode(stream1)
			streamTree.setActive(id1)
			streamTree.addNode(stream2)
			streamTree.addNode(stream3)
			streamTree.setActive(id3)
			streamTree.addNode(stream4)
			streamTree.setActive(id4)
			n1 := streamTree.nodeMap[id1]
			n2 := streamTree.nodeMap[id2]
			n3 := streamTree.nodeMap[id3]
			n4 := streamTree.nodeMap[id4]
			err := streamTree.maybeSetParent(id3, id2, false)
			Expect(err).NotTo(HaveOccurred())
			err = streamTree.maybeSetParent(id4, id2, false)
			Expect(err).NotTo(HaveOccurred())

			// Set n1 as exclusive child to n2
			err = streamTree.maybeSetParent(id1, id2, true)
			Expect(err).NotTo(HaveOccurred())

			// n2 should now be parent of n1
			Expect(n1.parent).To(Equal(n2))
			Expect(isParent(n2, n1)).To(BeTrue())
			Expect(len(n2.children)).To(Equal(1))

			// parent of n2 should not be changed
			Expect(n2.parent).To(Equal(streamTree.root))
			Expect(isParent(streamTree.root, n2)).To(BeTrue())
			Expect(len(streamTree.root.children)).To(Equal(1))

			// n1 should adopt n3 and n4 from n2
			Expect(n3.parent).To(Equal(n1))
			Expect(n4.parent).To(Equal(n1))
			Expect(isParent(n1, n3)).To(BeTrue())
			Expect(isParent(n1, n4)).To(BeTrue())
			Expect(len(n1.children)).To(Equal(2))
		})

		It("sets parent to a previous descendant", func() {
			//
			//		root                root
			//		  |                   |
			//        1        -->        2
			//        |                   |
			//        2                   1
			//       / \                 / \
			//      3   4               3   4
			//
			streamTree.addNode(headerStream)
			streamTree.addNode(stream1)
			streamTree.addNode(stream2)
			streamTree.addNode(stream3)
			streamTree.addNode(stream4)
			streamTree.setActive(id3)
			streamTree.setActive(id4)

			n1 := streamTree.nodeMap[id1]
			n2 := streamTree.nodeMap[id2]
			n3 := streamTree.nodeMap[id3]
			n4 := streamTree.nodeMap[id4]
			err := streamTree.maybeSetParent(id2, id1, false)
			Expect(err).NotTo(HaveOccurred())
			err = streamTree.maybeSetParent(id3, id2, false)
			Expect(err).NotTo(HaveOccurred())
			err = streamTree.maybeSetParent(id4, id2, false)
			Expect(err).NotTo(HaveOccurred())

			// Set n1 as exclusive child to n2
			err = streamTree.maybeSetParent(id1, id2, true)
			Expect(err).NotTo(HaveOccurred())

			// n2 should now be parent of n1
			Expect(n1.parent).To(Equal(n2))
			Expect(isParent(n2, n1)).To(BeTrue())
			Expect(len(n2.children)).To(Equal(1))

			// parent of n2 now be the root
			Expect(n2.parent).To(Equal(streamTree.root))
			Expect(isParent(streamTree.root, n2)).To(BeTrue())
			Expect(len(streamTree.root.children)).To(Equal(1))

			// n1 should adopt n3 and n4 from n2
			Expect(n3.parent).To(Equal(n1))
			Expect(n4.parent).To(Equal(n1))
			Expect(isParent(n1, n3)).To(BeTrue())
			Expect(isParent(n1, n4)).To(BeTrue())
			Expect(len(n1.children)).To(Equal(2))
		})
	})

	Context("setting active", func() {
		It("sets node active", func() {
			streamTree.addNode(stream1)
			streamTree.setActive(id1)
			Expect(streamTree.nodeMap[id1].state).To(Equal(nodeActive))
		})

		It("adds idle parents to the tree", func() {
			streamTree.addNode(headerStream)
			streamTree.addNode(stream1)
			streamTree.addNode(stream2)

			n1 := streamTree.nodeMap[id1]

			err := streamTree.maybeSetParent(id2, id1, false)
			Expect(err).NotTo(HaveOccurred())

			Expect(len(streamTree.root.children)).To(Equal(0))
			Expect(streamTree.root.activeChildren).To(Equal(uint16(0)))
			Expect(len(n1.children)).To(Equal(0))
			Expect(n1.activeChildren).To(Equal(uint16(0)))

			streamTree.setActive(id2)

			Expect(len(streamTree.root.children)).To(Equal(1))
			Expect(streamTree.root.activeChildren).To(Equal(uint16(1)))
			Expect(len(n1.children)).To(Equal(1))
			Expect(n1.activeChildren).To(Equal(uint16(1)))
		})

		It("does not add active parents to the tree", func() {
			streamTree.addNode(headerStream)
			streamTree.addNode(stream1)
			streamTree.addNode(stream2)
			streamTree.addNode(stream3)

			n1 := streamTree.nodeMap[id1]

			err := streamTree.maybeSetParent(id2, id1, false)
			Expect(err).NotTo(HaveOccurred())
			err = streamTree.maybeSetParent(id3, id1, false)
			Expect(err).NotTo(HaveOccurred())

			streamTree.setActive(id2)

			Expect(len(streamTree.root.children)).To(Equal(1))
			Expect(streamTree.root.activeChildren).To(Equal(uint16(1)))
			Expect(len(n1.children)).To(Equal(1))
			Expect(n1.activeChildren).To(Equal(uint16(1)))

			streamTree.setActive(id3)

			Expect(len(streamTree.root.children)).To(Equal(1))
			Expect(streamTree.root.activeChildren).To(Equal(uint16(1)))
			Expect(len(n1.children)).To(Equal(2))
			Expect(n1.activeChildren).To(Equal(uint16(2)))
		})

		It("does not set unknown stream active", func() {
			err := streamTree.setActive(id1)
			Expect(err).To(HaveOccurred())
		})
	})

	Context("scheduling", func() {

		It("returns nil if there is no data to send", func() {
			streamTree.addNode(stream1)
			streamTree.addNode(stream2)
			streamTree.addNode(stream3)
			streamTree.addNode(stream4)

			err := streamTree.maybeSetParent(id3, id1, false)
			Expect(err).ToNot(HaveOccurred())
			err = streamTree.maybeSetParent(id4, id1, false)
			Expect(err).ToNot(HaveOccurred())

			s := streamTree.schedule()
			Expect(s).To(BeNil())
		})

		//SHI
		It("schedules all stream", func() {
			// header stream and crypto stream never close
			streamTree.addNode(cryptoStream)
			streamTree.addNode(headerStream)

			streamTree.addNode(stream1) //4
			streamTree.addNode(stream2) //5
			streamTree.addNode(stream3) //6
			streamTree.addNode(stream4) //7

			err := streamTree.maybeSetParent(6, 4, false)
			Expect(err).ToNot(HaveOccurred())
			err = streamTree.maybeSetParent(7, 6, false)
			Expect(err).ToNot(HaveOccurred())

			//	stream1.dataForWriting = []byte("foobar")
			all := streamTree.traverseAll(streamTree.root)
			Expect(len(all)).To(Equal(6)) //all streams

		})

		//SHI
		It("schedules stream only after its parent finished", func() {
			// header stream and crypto stream never close
			streamTree.addNode(cryptoStream)
			streamTree.addNode(headerStream)

			streamTree.addNode(stream1) //4
			streamTree.addNode(stream2) //5
			streamTree.addNode(stream3) //6
			streamTree.addNode(stream4) //7

			err := streamTree.maybeSetParent(6, 4, false)
			Expect(err).ToNot(HaveOccurred())
			err = streamTree.maybeSetParent(7, 6, false)
			Expect(err).ToNot(HaveOccurred())

			s := streamTree.schedule()

			Expect(len(s)).To(Equal(4)) //crypto stream, header stream, stream id = 4,5
			s = streamTree.schedule()
			Expect(len(s)).To(Equal(0))

			stream1.finishedWriting.Set(true) //stream id = 4
			stream1.finSent.Set(true)

			s = streamTree.schedule()
			Expect(len(s)).To(Equal(1))

			stream3.finishedWriting.Set(true)
			stream3.finSent.Set(true)

			s = streamTree.schedule()
			Expect(len(s)).To(Equal(1))

		})

		//SHI
		It("print streamTree", func() {
			// header stream and crypto stream never close
			streamTree.addNode(cryptoStream)
			streamTree.addNode(headerStream)

			streamTree.addNode(stream1) //4
			streamTree.addNode(stream2) //5
			streamTree.addNode(stream3) //6
			streamTree.addNode(stream4) //7

			err := streamTree.maybeSetParent(6, 4, false)
			Expect(err).ToNot(HaveOccurred())
			err = streamTree.maybeSetParent(7, 6, false)
			Expect(err).ToNot(HaveOccurred())

			streamTree.printTree()

		})

		It("schedules visited stream under dynamic case", func() {
			// header stream and crypto stream is always scheduled
			// because we only check the size of normal streams in scheduling
			// but if the two streams are already scheduled onto a path, we will skip path scheduling for them
			streamTree.addNode(cryptoStream)
			streamTree.addNode(headerStream)
			streamTree.addNode(stream1) //4
			streamTree.addNode(stream2) //5
			streamTree.addNode(stream3) //6
			streamTree.addNode(stream4) //7

			err := streamTree.maybeSetParent(6, 4, false)
			Expect(err).ToNot(HaveOccurred())
			err = streamTree.maybeSetParent(7, 6, false)
			Expect(err).ToNot(HaveOccurred())

			s := streamTree.schedule()
			Expect(len(s)).To(Equal(4))
			s = streamTree.schedule()
			Expect(len(s)).To(Equal(4))
			s = streamTree.schedule()
			Expect(len(s)).To(Equal(4))

			stream1.finishedWriting.Set(true) //stream id = 4
			stream1.finSent.Set(true)
			stream1.checksize = true

			stream2.finishedWriting.Set(true) //stream id = 5
			stream2.finSent.Set(true)
			stream2.checksize = true

			s = streamTree.schedule()
			Expect(len(s)).To(Equal(3))

			stream3.finishedWriting.Set(true)
			stream3.finSent.Set(true)

			s = streamTree.schedule()
			Expect(len(s)).To(Equal(3))

		})
	})
})
